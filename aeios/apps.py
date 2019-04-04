# -*- coding: utf-8 -*-

import re
import os
import logging
import datetime as dt

import config
from device import DeviceList
from actools import adapter, cfgutil
from distutils import version

"""
Manage Apps for iOS devices
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "2.3.0"
__all__ = ['App',
           'AppError',
           'AppList',
           'AppManager',
           'RecoveryError']

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

class Error(Exception):
    """
    Base Exception
    """
    pass


class AppError(Error):
    pass


class RecoveryError(Error):

    def __init__(self, alert):
        self.alert = alert

    def __str__(self):
        return self.alert.message


class VerificationError(Error):
    pass


class SkipVerification(Error):
    pass


class App(object):

    def __init__(self, record, path=None):
        self.name = u"{0!s}".format(record['itunesName'])
        self.version = version.LooseVersion(record['bundleVersion'])
        self.displayname = record['displayName']
        self.identifier = record['bundleIdentifier']
        # self.path = os.path.join(path, self.name, str(self.version))
        self._file = None

    def __eq__(self, x):
        return self.name == x.name and self.version == x.version

    def __lt__(self, x):
        if self.name != x.name:
            raise AppError("unable to compare different apps")
        return self.version < x.version

    def __gt__(self, x):
        if self.name != x.name:
            raise AppError("unable to compare different apps")
        return self.version > x.version

    def __repr__(self):
        return u"App({0!r})".format(self.name)

    def __str__(self):
        return self.name.encode('utf-8')

    def __unicode__(self):
        return self.name

    @property
    def record(self):
        return {'itunesName': self.name,
                'bundleVersion': str(self.version),
                'displayName': self.displayname,
                'bundleIdentifier': self.identifier}

    @property
    def file(self):
        if not self._file:
            try:
                _files = [x for x in os.listdir(self.path) if x.endswith('.ipa')]
                self._file = os.path.join(self.path, _files[-1])
            except (OSError, IndexError):
                pass
        return self._file


class AppList(list):
                
    @property
    def names(self):
        return [x.name for x in self]

    @property
    def identifiers(self):
        return [x.identifier for x in self]

    def find(self, a):
        try:
            return [app for app in self if app == a][0]
        except IndexError:
            return a

    def app(self, name):
        return [app for app in self if app.name == name][0]

    def __repr__(self):
        return "AppList({0!r})".format(self.names)

    def __unicode__(self):
        # u'\u201d, \u201c'
        return u'“{0!s}”'.format(u'”, “'.join(self.names))

    def __str__(self):
        names = [x.encode('utf-8') for x in self.names]
        return '"{0!s}"'.format('", "'.join(names))


class Hook(object):
    """
    Hook into specific stage of installation
    """
    def __init__(self):
        self.callback = None
        self.trigger = None


class Monitor(object):
    """
    Monitors installation
    """
    def __init__(self):
        self.hook = None  # callback to hook
        self.recovery = None  # callback to recovery
        self.result = None  # result of recovery
        self.alerts = []  # list of encountered alerts


class AlertRecord(object):

    def __init__(self, data, alert=None):
        if alert:
            self.alert = alert
            self.count = 1
            self.similar = 0
        else:
            self.alert = adapter.Alert.load(data['alert'])
            self.count = data.get('count', 1)
            self.similar = data.get('similar', 0)

    def record(self):
        return {'alert': self.alert.record, 'timestamp': timestamp,
                'count': self.count, 'similar': self.similar}

    @classmethod
    def from_alert(cls, alert):
        return cls({}, alert)


class AlertManager(object):
    """
    Alert tracking
    """
    def __init__(self, name, resources):
        self.log = logging.getLogger(__name__ + '.AlertManager')
        _id = "{0}.errors".format(name)
        self.config = config.Manager(_id, path=resources.path)

        try:
            self.config.read()
        except config.Missing as e:
            self.log.error(e)
            _default = {'Errors': ()}
            self.log.debug("creating default: %s", _default)
            self.config.write(_default)
            
    def __bool__(self):
        return True if self.error else False

    __nonzero__ = __bool__

    @property
    def count(self):
        return len(self.errors)

    @property
    def error(self):
        try:
            self.log.debug("returning: %r", self.errors[-1])
            return self.errors[-1]
        except IndexError:
            self.log.debug("no errors")
            pass

    @error.setter
    def error(self, value):
        self.log.debug("adding value: %r", value)
        _errors = self.errors + [value]
        self.config.reset('Errors', _errors)

    def add(self, value):
        self.log.debug("adding value: %r", value)
        self.error = value

    @property
    def errors(self):
        return self.config.setdefault('Errors', ())

    @errors.setter
    def errors(self, value=()):
        self.log.debug("reseting value: %r", value)
        return self.config.reset('Errors', value)
                
    def clear(self):
        self.log.debug("clearing")
        return self.config.reset('Errors', [])
    

class AppManager(object):
    
    default = {'groups': {'model': {'iPad7,3': ['iPadPros'],
                                    'iPad8,1': ['iPadPros'],
                                    'iPad7,5': ['iPads']}},
               'all': [],
               'all-iPads': [],
               'iPadPros': [],
               'iPads': []}
                     
    def __init__(self, _id, resources):
        # needs the manager to ask for installed apps
        # or the list of installed apps needs to be provided <--
        self.log = logging.getLogger(__name__)

        self.resources = resources
        a_id = "{0}.apps".format(_id)
        path = str(self.resources)
        self.config = config.Manager(a_id, path=path)
        self.file = self.config.file
        self.errors = AlertManager(a_id, resources)
        # read global App configuration (if any)
        _apps = self.__class__.default
        try:
            g_path = path.replace(os.path.expanduser('~'), '')
            g_config = config.Manager(a_id, path=g_path)
            # repopulate defaults with settings from global config
            _apps = g_config.read()
            # overwrite existing apps with global configuration
            self.config.write(_apps)
        except config.Error:
            self.log.debug("no global configuration for apps")
            pass

        try:
            # TO-DO: merge from /Library
            self._record = self.config.read()
            self.log.debug("found configuration: %s", self.file)
        except config.Error as e:
            self.log.error("unable to read config: %s", e)
            self.log.info("creating new config from default")
            self.log.debug("writing config: %r", _apps)
            self.config.write(_apps)
            self._record = self.config.read()
            
        adapter.log = os.path.join(self.resources.logs, 'acadapter.log')  

        self._apps = AppList()
        self.alerts = []

    @property
    def error(self):
        return self.errors.error
        
    # TO-DO: remove
    @property
    def record(self):
        """
        :return: dict of config as read from disk
        """
        return self.config.read()

    def groups(self, device=None):
        """
        :return: list of groups device belongs to
        """
        if device is not None:
            # strip device type from model identifier ('iPad7,5' -> 'iPad')
            model_type = re.match(r'^(\w+?)\d+,\d+$', device.model).group(1)
            groupnames = ['all', "all-{0!s}s".format(model_type)]
            groupset = set(groupnames)
            # model-only support for now
            _membership = self._record['groups']['model'][device.model]
            groupset.update(_membership)
            return list(groupset)
        _excluded = ['groups', 'Identifiers', 'errors']
        return [x for x in self._record.keys() if x not in _excluded]
        
    def list(self, device=None, exclude=()):
        """
        :returns: list of (de-duplicated) apps scoped for device
        """
        appset = set()
        for group in self.groups(device):
            appset.update(self._record[group])
        appset.difference_update(exclude)
        return list(appset)

    def membership(self, model):
        """
        :return: list of all groups devices belongs to
        """
        # strip device type from model identifier ('iPad7,5' -> 'iPad')
        device_type = re.match(r'^(\w+?)\d+,\d+$', model).group(1)
        
        # return all groups
        _groups = self.groups
        _groups = ['All', 'All-{0!s}'.format(device_type)]
        members = {}
        for _type, v in self.config.get('groups', {}).items():
            for _id, groups in v.items():
                if name in groups:
                    g = members.setdefault(_type, [])
                    g.append(_id)
        return members

    def group(self, name):
        """
        :param name: name of group
        :return: dict of apps and members for group
        """
        return {'apps': list(self._record[name]), 
                'members': self.membership(name)}

    def add(self, group, apps):
        """
        Mechanism for adding apps to a group
        """
        _apps = self.config.get(group)
        if not _apps:
            appset = set(apps)
            self.config.update({group: list(appset)})
        else:
            # update existing group apps (excluding duplicates)
            appset = set(_apps + apps)
            self.config.update({group: list(appset)})
        self._record = self.config.read()
        return list(appset)

    def remove(self, group, apps):
        """
        Remove apps from specified group

        :returns: list of apps in group (after removal)
        """
        _apps = self.config.get(group)
        if not _apps:
            return []
        else:
            # update existing group apps (excluding duplicates)
            appset = set(_apps) - set(apps)
            self.config.update({group: list(appset)})
        self._record = self.config.read()
        return list(appset)

    def unknown(self, device, appnames=None):
        """
        :returns: AppList of unknown apps (new apps)
        """
        applist = AppList([App(x) for x in device.apps])
        if not appnames:
            appset = set(applist.names)
        else:
            appset = set(appnames)
        appset.difference_update(self.list())
        return AppList([x for x in applist if x.name in appset])            

    # TO-DO: fix/remove this
    def breakdown(self, devices):
        """
        NOTE:
            I hate this and it's temporary but should (unintelligently)
            return two instruction sets:
                [([<all devices>], [<all ipad apps>]),
                ([<all iPad Pros>], [<all iPad Pro apps>])]
            the second instruction set is only returned if iPad Pros 
            (iPad7,3) are included in the device list 
        """
        _all = self._record['all']
        _ipads = self._record['all-iPads']

        # create a list of all unique apps for all iPads
        _breakdown = [(devices, list(set(_all).union(_ipads)))]

        if self._record['iPads']:
            ipads = [x for x in devices if x.model == 'iPad7,5']
            if ipads:
                # add second instruction set for iPads (if any)
                # TO-DO: this will add an empty instruction set
                _breakdown.append((ipads, self._record['iPads'])) 

        # check if iPad pros are included in the specified devices
        ipadpros = [x for x in devices if x.model == 'iPad7,3']
        if ipadpros and self._record['iPadPros']:
            # add third instruction set for iPad Pros (if any)
            _breakdown.append((ipadpros, self._record['iPadPros'])) 
        return _breakdown

    def installed(self, devices):
        """
        :param devices: DeviceList
        :return: list of app names that are commonly installed
        """
        # set of all installed app names for all specified devices
        _installed = set().union([App(a).name for d in devices for a in d.apps])
        self.log.debug("_installed: %r", _installed)
        for device in devices:
            # names = AppList([app for app in device.apps]).names
            _apps = [app for app in device.apps]
            self.log.debug("_apps: %r", _apps)
            _applist = AppList(App(a) for a in _apps)
            self.log.debug("_applist: %r", _applist)
            names = _applist.names
            self.log.debug("names: %r", names)
            _installed.intersection_update(names)
        # TO-DO: returns set, should return list?
        return _installed

    @staticmethod
    def installedapps(devices):
        """
        :param devices:
        :return: list of apps installed
        """
        # TO-DO: run per device, requires re-work of cfgutil
        #        has to work with entire device list for now
        results = cfgutil.get(['installedApps'], devices.ecids)
        apps = []
        for device in devices:
            _apps = results.get(device.ecid, {}).get('installedApps', [])
            device.apps = _apps
            apps += [x for x in _apps if x not in apps]

        return apps

    @property
    def recovery(self):
        """
        :returns: callback to performed in the case of an alert
        """
        alerts = self.alerts

        def _recovery(alert):
            # skip common errors until something better can be implemented
            logger = logging.getLogger(__name__)
            if alerts:
                logger.debug("previous alerts were found")
                for a in alerts:
                    if a == alert:
                        logger.error("same alert occurred: %s", alert)
                        logger.debug("%r", alert)
                        raise RecoveryError(alert)
            else:
                logger.debug("no previous alerts")

            alerts.append(alert)

            if "unknown error" in [alert.message, alert.details]:
                logger.critical("unknown error: %s", alert)
                raise alert

            elif "already exists on" in alert.message:
                logger.debug(u"skipping installed app: %s", alert)
                adapter.action("Skip App", ["Apply to all apps"])
            
            elif "An unexpected network error occurred" in alert.details:
                logger.debug(u"attempting to retry network: %s", alert)
                adapter.action("Try Again")

            else:
                raise RecoveryError(alert)

        return _recovery
    
    def install_vpp_apps(self, devices):
        if not devices:
            self.log.error("no devices specified")
            return

        tasked = self.needs_apps_installed(devices)
        if not tasked:
            self.log.info("no apps need to be installed for: %s", devices)
            return

        def _hook(func, path):
            def _wrapped():
                func(path)
            return _wrapped

        wrapped = _hook(copy_apps, self.resources.apps)
        
        for _devices, apps in self.breakdown(tasked):
            try:
                self.log.debug("breakdown: %s: %r", _devices, apps)
                self.log.debug("looking for commonly installed apps")
                _installed = self.installed(_devices)
                self.log.debug("already commonly installed: %r", _installed)
                self.log.debug("updating applist")
                _apps = list(set(apps).difference(_installed))
                self.log.debug("new applist: %r", _apps)
                self.log.info("installing: %r: %s", _apps, _devices)
                adapter.install_vpp_apps(_devices.udids, _apps, self.recovery, 
                                         hook=hook('Installing', wrapped))
            except adapter.ACStalled as e:
                self.log.error(u"stalled: %s", e)
                self.errors.add({'error': 'stalled',
                                 'timestamp': dt.datetime.now()})
                adapter.relaunch()
                raise
            except adapter.Alert as alert:
                self.log.error(u"unexpected alert: %s", alert)
                self.errors.add({'error': 'alert',
                                 'timestamp': dt.datetime.now()})
                raise
            except adapter.ACAdapterError as e:
                self.log.error(u"execution failed: %s", e)
                self.errors.add({'error': 'execution',
                                 'timestamp': dt.datetime.now()})
                raise

    def install_local_apps(self, devices):
        """
        Hack to install apps from local .ipa files
        currently there is no mechanism to store .ipa files
        nor do I have any immediate plans to support or
        """
        # TO-DO: need to organize local app storage and create hook
        #        to trigger local app copy
        #       - need to hook into install_vpp_apps()
        #           - wait for "Downloading apps" to disappear
        #           - requires hook
        path = self.resources.apps
        apps = [x for x in os.listdir(path) if x.endswith('.ipa')]
        if not apps:
            self.log.debug("no local apps were found")
            return

        self.log.debug("local apps: '%s'", "', '".join(apps))
        paths = [os.path.join(path, x) for x in apps]

        try:
            self.log.info("installing local apps on: %s", devices)
            cfgutil.cfgutil('install-apps', devices.ecids, paths)
            self.log.debug("local apps successfully installed")
        except cfgutil.Error as e:
            self.log.error("failed to install local apps")
            self.log.error(e)

    def apps(self, records):
        """
        Retrieves known app objects
        
        :param records:
        :return:
        """
        _apps = AppList()
        for app in [App(x) for x in records]:
            app = self._apps.find(app)
            if app not in self._apps:
                self._apps.append(app)
            _apps.append(app)
        return _apps

    def needs_apps_installed(self, devices):
        """
        Excludes devices that don't need apps installed

        :param devices: DeviceList
        :return: DeviceList of devices with uninstalled apps
        """
        # self.installedapps(devices)
        needs_apps = DeviceList()
        for device in devices:
            installed = self.apps(device.apps)
            if self.list(device, exclude=installed.names):
                needs_apps.append(device)
        return needs_apps
    
    @property
    def verified(self):
        """
        Not implemented
        """
        return self.config.setdefault('verified', False)

    @verified.setter
    def verified(self, value):        
        """
        Not implemented
        """
        if not isinstance(value, bool):
            raise TypeError("{0}: not boolean".format(value))
        self.config.update({'verified': value})

    def verify(self, devices, force=False):
        """
        Verify App installation on devices

        :param devices: DeviceList
        :type devices: device.DeviceList

        :return: DeviceList of devices that failed app installation
        """
        # NOTE: relies on external device.app record update (for now)
        self.log.debug("checking installed apps: %s", devices) 
        _missing = self.needs_apps_installed(devices)
        if force:
            self.log.debug("forcing verification: %s", devices) 
            self.log.debug("errors will not be recorded or reset")
            return _missing

        now = dt.datetime.now()
        if not _missing:
            self.log.info("all apps installed: %s", devices)
            self.log.debug("clearing all errors")
            self.errors.clear()
            self.log.debug("errors: %r", self.errors.errors)
        
        elif self.errors.count > 3:
            # get last error
            self.log.error("multiple errors detected")
            self.log.debug("last error: %r", self.error.error)
            retry = self.errors.error['timestamp'] + dt.timedelta(hours=1)
            if now < retry:
                self.log.debug("skipping verification")
                raise SkipVerification("app verification skipped")

        # TO-DO: this seems sloppy (fix me)
        if _missing:
            self.log.error("apps missing: %s", _missing)
            self.log.debug("current errors: %s", self.errors)
            self.errors.add({'error': 'verification', 
                             'timestamp': now})
            self.log.debug("updated errors: %s", self.errors)

        self.log.debug("missing apps: %r", _missing)
        return _missing


def hook(trigger, callback):
    # mutable var so we can bleed out of namespace
    _hook = {'done': False}

    def _wrapper(status):
        """
        Single time execution of hook on status
        :param status: adapter.Status()
        :return: None
        """
        if not _hook['done'] and trigger in status.details:
            callback()
            # bleed out of scope
            _hook['done'] = True

    return _wrapper


def copy_apps(path):
    logger = logging.getLogger(__name__)
    logger.debug("copying local app files: %s", path)


if __name__ == '__main__':
    pass
