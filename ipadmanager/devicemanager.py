# -*- coding: utf-8 -*-

import os
import logging
import time

from datetime import datetime, timedelta

import config
from tasklist import TaskList
from device import Device, DeviceError
from appmanager import AppManager
from actools import adapter, cfgutil
import tethering

try:
    from management_tools import slack
except ImportError:
    slack = None

'''Collection of tools for managing and automating iOS devices
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '2.1.6'
__url__ = None
__description__ = ('Collection of tools for managing and automating '
                   'iOS devices')
__all__ = [
    'DeviceManager', 
    'StoppedError',
    'Slackbot'
]

## CHANGELOG:
# 2.0.1:
#   - added default supervision and image directories
# 2.0.2:
#   - added slack from management_tools
# 2.0.3:
#   - minor adjustments and fixes
#
# 2.1.0:
#   - changed:
#       - waitfor(): included better looping and locking
#       - available(): only returns devices that are currently connected
#       - unavailable(): inverse of available()
#       - query(): now checks for installed apps (incomplete)
#       - run():
#           - changed erase to exist outside of the stop lock
#           - added timestamp to finished
#           - exit mechanism checks if any tasks need to be done
#  - added:
#       - verify(): waits for restart
#                   still incomplete but working
#       - verified: fixes some egregious errors before running
#                   still incomplete but working
#       - locked: variant of quarantine (incomplete)
#       - devicelist: checks currently connect devices, caches list
#                     for 30 seconds
# 2.1.1:
#   - incorporated appmanager 2.1.0
#   - added bit to identify new apps and slack the info (also locks)
# 2.1.2:
#   - changed lock() to lockdevices()
#       - fixed bug where devices would not lock (needs testing)
#   - added fixes from appmanager 2.1.1
#   - fixed slack reporting for new apps (no longer sends empty list)
# 2.1.3:
#   - minor fixes with lockdevices() and locked
#   - fixed bug where query would always lock devices
# 2.1.4:
#   - fixed bug where background would be changed back and forth on 
#     locked devices
#   - fixed bug where device could be listed before a record was created
# 2.1.5:
#   - modified printing of device locking
#   - fixed bugs that would cause the device to not be removed from erase
#     list
#   - incorporated changes from cfgutil 2.0.5
#   - added better erase error detection
# 2.1.6:
#   - Moved Slackbot to __init__.py
#   - changed query()
#   - removed lockcheck from need_to_erase
# 2.1.7:
#   - Moved Slackbot back to devicemanager (couldn't import)

## BUGS:
# - new devices are causing the manager to exit (fixed in 2.1.4)


class Error(Exception):
    pass


class StoppedError(Error):
    '''Exception to interrupt and signal to other DeviceManagers
    '''
    def __init__(self, message, reason=None):
        super(self.__class__, self).__init__(message)
        self.reason = reason

    def __str__(self):
        return "STOPPED: " + str(self.message)


class Slackbot(object):
    '''Null Wrapper for management_tools.slack
    '''
    def __init__(self, info, logger=None):
        if not logger:
            logger = logging.getLogger(__name__)
            logger.addHandler(logging.NullHandler())
        self.log = logger
        try:
            # TO-DO: name could be dynamic
            self.name = info['name']
            self.channel = info['channel']
            self.url = info['url']
            self.bot = slack.IncomingWebhooksSender(self.url, 
                               bot_name=self.name, channel=self.channel)
            self.log.info("slack channel: {0}".format(self.channel))
        except AttributeError as e:
            self.log.error("slack tools not installed")
            self.bot = None            
        except KeyError as e:
            self.log.error("missing slack info: {0}".format(e))
            self.bot = None
    
    def send(self, msg):
        try:
            self.bot.send_message(msg)
        except AttributeError:
            self.log.debug("slack: unable to send: {0}".format(msg))
            pass


class DeviceManager(object):
    
    def __init__(self, id, logger=None, **kwargs):
        if not logger:
            logger = logging.getLogger(__name__)
            logger.addHandler(logging.NullHandler())
        self.log = logger

        self.lock = config.FileLock('/tmp/ipad-manager', timeout=5)
        c_id = "{0}.manager".format(id)
        self.config = config.Manager(c_id, **kwargs)
        self.file = self.config.file
        try:
            self.config.read()
        except config.Error:
            self.log.error("failed to load: {0}".format(self.file))
            self.config.write({})
            
        self.file = self.config.file
        location = os.path.dirname(self.file)
        self._devicepath = os.path.join(location, 'devices')
        try:
            os.mkdir(self._devicepath)
        except OSError as e:
            if e.errno != 17:
                raise

        # self.log.debug("config: {0}".format(self.record))
        slack = self.config.get('slack', {})
        # self.log.debug("slack info: {0}".format(slack))
        self.slackbot = Slackbot(slack, logger=self.log)

        self.task = TaskList(id, path=location, logger=self.log)
        self.apps = AppManager(id, path=location, logger=self.log)

        self._lookup = self.config.setdefault('devices', {})
        self.idle = self.config.setdefault('idle', 300)
        _quarantine = self.config.setdefault('quarantine', [])
        self._quarantined = set(_quarantine)
        
        _imagedir = os.path.join(location, 'images')
        self._images = self.config.get('images', _imagedir)

        _authdir = os.path.join(location, 'supervision')
        self._supervision = self.config.get('supervision', _authdir)

        # self._devices = []
        self._device = {}
        self._erased = []
        self._list = None
        self._auth = None

    @property
    def record(self):
        return self.config.read()                

    @property
    def checkedout(self):
        _checked_out = []
        for device in self.findall():
            try:
                if device.checkout > device.checkin:
                    _checked_out.append(device.ecid)
            except:
                pass
        return _checked_out

    @property
    def checkedin(self):
        _checked_in = []
        # self.log.debug("checkedin: looking for checked in devices")
        for device in self.findall():
            # self.log.debug("checkedin: checking: {0}".format(device.ecid))
            try:
                if device.checkin > device.checkout:
                    _checked_in.append(device.ecid)
            except TypeError:
                _checked_in.append(device.ecid)
        # self.log.debug("checkedin: {0}".format(_checked_in))
        return _checked_in
        
    def available(self, ecids=False):
        '''Returns list of all devices (or device ECID's) that are
        currently checked in
        '''
        devices = self.findall([i['ECID'] for i in self.devicelist()])
        if ecids:
            return [d.ecid for d in devices]
        return devices

    def unavailable(self, ecids=False):
        '''Returns list of all devices (or device ECID's) that are
        currently checked out
        '''
        devices = self.findall(exclude=self.available())
        if ecids:
            return [d.ecid for d in devices]
        return devices

    def findall(self, ecids=None, exclude=[]):
        '''returns list of Device objects for specified ECIDs
        '''
        if ecids is None:
            if not self._lookup:
                self.log.debug("lookup was reset... refreshing")
                self._lookup = self.config.get('devices', {})
            ecids = self._lookup.keys()

        try:
            devices = [self.device(x) for x in ecids 
                           if x not in exclude]
        except:
            self.log.error("failed to find devices")
            self.log.debug("attempting to recover...")
            # an error can be thrown if findall() is called before
            # a device record has been created
            devices = []
            for info in self.devicelist():
                ecid = info['ECID']
                if ecid in ecids:
                    devices.append(self.device(ecid, info))
        return devices
            
    def device(self, ecid, info={}):
        '''Returns Device object from ECID
        '''
        # return a cached device object (if we have one)
        try:    
            return self._device[ecid]
        except KeyError:
            pass        

        # initialize device object from disk, and cache it
        try:
            # use the lookup table to translate the ECID -> UDID
            udid = self._lookup[ecid]
            _device = Device(udid, info, path=self._devicepath)
            self._device[ecid] = _device
            return _device
        except KeyError:
            self.log.debug("no device record found")
            pass
        
        # no existing device 
        self.log.debug("creating new device record")
        udid = info['UDID']
        ecid = info['ECID']
        _device = Device(udid, info, path=self._devicepath)
        lock = config.FileLock('/tmp/new-device', timeout=5)
        with lock.acquire():
            _lookup = self.config.get('devices', {})
            _lookup.update({ecid: udid})
            self.config.update({'devices': _lookup})
            # force a refreshed lookup first time findall() is called
            self._lookup = {}
            self._device[ecid] = _device
        _device.restarting = False
        self.task.query('serialNumber', [ecid])
        self.task.erase([ecid])
        
        return _device
                               
    def supervised(self, devices):
        raise Error("Not Implemented")

    def devicelist(self, refresh=False):        
        '''Returns list of Device objects using cfgutil.list()
        '''
        # attempt to keep listing down to once per 30 seconds
        now = datetime.now()
        _stale = now - timedelta(seconds=30)
        _listed = self.config.get('listed')
        if refresh or not self._list or _listed < _stale:        
            self.log.debug("refreshing device list")
            self._list = cfgutil.list(log=self.log)
            self.config.update({'listed': now})
        # else:
        #     self.log.debug("using cached device list")

        return self._list

    def need_to_erase(self, device):
        '''Reserved for future conditional erasing
        Returns True (for now)
        '''
        # self.task.add('lockcheck', [device.ecid])
        device.delete('erased')
        self.task.query('installedApps', [device.ecid])
#         if device.locked:
#             return False
        return True

    def check_network(self, devices):    
        if not tethering.enabled(self.log):
            self.log.error("tethered-caching wasn't enabled...")
            tethering.restart(self.log, timeout=20)
    
        serialnumbers = [d.serialnumber for d in devices]
        tethered = tethering.devices_are_tethered(self.log, 
                                                  serialnumbers)
        timeout = datetime.now() + timedelta(seconds=30)
        while not tethered:
            time.sleep(5)
            tethered = tethering.devices_are_tethered(self.log, 
                                                      serialnumbers)
            if datetime.now() > timeout:
                break
                
        if not tethered:
            tethering.restart(self.log, timeout=20)

    def checkin(self, info):
        '''
        '''
        device = self.device(info['ECID'], info)
        
        if self.stopped:
            self.waitfor(device, 'restart')                

        if device.name.startswith('iPad'):
            name = "{0} ({1})".format(device.name, device.ecid)
        else:
            name = device.name

        erase = False
        if not device.checkin:
            self.log.debug("{0}: never checked in".format(name))
            erase = self.need_to_erase(device)
        else:
            try:
                checkedout = device.checkout > device.checkin
            except TypeError:
                self.log.debug("{0}: never checked out".format(name))
                checkedout = False
            
            if checkedout:
                self.log.info("{0}: was checked out".format(name))
                erase = self.need_to_erase(device)
            else:
                self.log.info("{0}: was not checked out".format(name))

        if erase:
            self.log.info("{0}: will be erased".format(name))
            self.task.erase([device.ecid])
        else:
            self.log.debug("{0}: will not be erased".format(name))
            
        device.checkin = datetime.now()
        self.run(device.ecid)

    def checkout(self, info):
        '''saves timestamp of device checkout (if not restarting)
        '''
        device = self.device(info['ECID'], info)

        # skip checkout if device has been marked for restart
        if device.name.startswith('iPad'):
            name = "{0} ({1})".format(device.name, device.ecid)
        else:
            name = device.name
        
        if device.restarting:
            self.log.info("{0}: restarting...".format(name))
            # self.task.add('network', [device.ecid])
            device.restarting = False
        else:
            self.log.info("{0}: checked out".format(name))            
            device.checkout = datetime.now()

    def waitfor(self, device, reason):
        '''Placeholder for waiting for restart
        '''
        # if stopped, but we don't have a reason
        if self.stopped and not self.config.get('reason'):
            self.log.debug("stopped for no reason...")
            self.stopped = False
            return

        self.log.debug("instructed to wait for: {0}".format(reason))
        if reason != self.config.get('reason'):
            raise StoppedError("not stopped for: {0}".format(reason))

        # get this device's ecid out of the queue (if it's there)
        self.task.get(reason, only=[device.ecid])

        ## this should block all devices until the stopped reason
        ## has passed
        self.log.debug("waiting for: {0}".format(reason))
        lockfile = '/tmp/ipad-{0}.lock'.format(reason)
        lock = config.FileLock(lockfile)
        with lock.acquire(timeout=-1):
            waiting = self.task.list(reason)
            if not waiting:                
                if self.stopped and self.config.get('reason'):
                    self.stopped = False
                    self.config.delete('reason')
                return

            stoptime = datetime.now() + timedelta(seconds=30)
            while waiting:
                time.sleep(2)
                self.log.debug("waiting on {0}: {1}".format(reason, 
                                                            waiting))
                waiting = self.task.list(reason)
                if datetime.now() > stoptime:
                    ecids = self.task.get(reason)
                    self.log.debug("gave up waiting")
                    break                            
            self.stopped = False
            self.config.delete('reason')

    def query(self):
        self.log.debug("checking for device queries")

        available = self.available(ecids=True)
        check_locked = self.task.get('lockcheck', only=available)
        if check_locked:
            self.task.query('cloudBackupsAreEnabled', check_locked)
            self.task.query('installedApps', check_locked)

        if not self.task.queries():
            self.log.info("no queries to perform")
            return
            
        cache = {}
        ecidset = set()
        # merge all of the queries into one 
        for query in self.task.queries():
            cache[query] = self.task.query(query)
            ecidset.update(cache[query])

        self.log.debug("query: {0} on {1}".format(cache.keys(), ecidset))
        failed = {}
        info = {}
        missing = []
        try:
            # TO-DO: cfgutil.get() needs to return two dicts and list
            self.log.debug("{0}: {1}".format(cache.keys(), ecidset))
            info, failed, missing = cfgutil.get(cache.keys(), ecidset, 
                                                           log=self.log)
            self.log.debug("info: {0}".format(info))
        except cfgutil.CfgutilError as e:
            self.log.error(e)
            for k,ecids in cache.items():
                if k != 'cloudBackupsAreEnabled':
                    m = 're-adding query: {0}: {1}'.format(k, ecids)
                    self.log.debug(m)
                    self.task.query(k, ecids)
            return

        if check_locked:
            _locked = []
            for device in self.findall(check_locked):
                _info = info.get(device.ecid, {})
                if _info.get('cloudBackupsAreEnabled') is not None:
                    _locked.append(device.ecid)

        for device in self.findall(ecidset):
            self.log.debug("unlocking device")
            device.delete('locked')
            # parse the info for the appmanager
            app_info = info.get('installedApps', [])
            # each app has 4 keys: 
            #   ['itunesName', 'displayName', bundleIdentifier, 
            #     'bundleVersion']
            # display name is useful only when parsing GUI
            # we install apps with their itunesName
            _apps = []
            for app in app_info:
                name = app.get('itunesName')
                if name:
                    _apps.append(name)
            # get all new apps that were installed (if any)
            _new = self.apps.unknown(device, _apps)
            if _new:
                # only report if new apps were found
                smsg = "new user apps: {0}".format(_new)
                msg = "NEW: {0}: {1}".format(device.name, smsg)
                self.log.info(msg)
                self.slackbot.send(msg)

            
        # TO-DO: this is dependent on how failed cfgutil.get returns
        # re-add failed queries
        for ecid,err in failed.items():
            # need to test if errors are returned as list
            for q in err:
                self.task.query(q, ecid)

        # re-add all queries for devices that went missing
        if missing:
            for k,ecids in cache.items():
                _missing = [x for x in ecids if x in missing]        
                self.task.query(k, _missing)

        # update devices with info
        for device in self.available(ecids=False):
            # not every device may have been queried
            _info = info.get(device.ecid, {})
            try:
                for k,v in _info.items():
                    if v is not None:
                        device.update(k, v)
            except:
                self.log.error("unable to update device")

    def erase(self, devices):
        if devices:
            _available = self.available()
            for device in devices:
                if device not in _available:
                    self.log.error("cannot prepare unavailable device")
        else:
            devices = self.available()

        ecids = self.task.erase(only=[d.ecid for d in devices])

        if not ecids:
            self.log.info("no devices need to be erased")
            return devices

        # reset device list to only tasked devices
        _devices = self.findall(ecids)
        # mark all devices to be erased as restarting
        for device in _devices:
            device.restarting = True
            device.erased = None
    
        erased = []
        missing = []
        try: 
            self.log.info("erasing devices: {0}".format(ecids))
            erased, missing = cfgutil.erase(ecids, log=self.log)
            self.task.erase(missing)
            self.task.prepare(erased)
        except cfgutil.CfgutilError as e:
            self.log.error("erase failed: {0}".format(e))
            if "complete the activation process" in e.message:
                err = "unable to erase activation locked device"
                self.log.error(err)
                self.slackbot.send(err)
                devices = self.findall(e.affected)
                self.lockdevices([d.ecid for d in devices])
                self.task.erase(e.unaffected)
            else:
                self.task.erase(e.affected)
        except Exception as e:
            self.log.error("erase: unexpected error: {0}".format(e))
            self.log.info("re-tasking erase: {0}".format(ecids))
            self.task.erase(ecids)
            # self.quarantine(ecids)
    
        if missing:
            self.log.error("devices went missing: {0}".format(missing))
            for device in self.findall(missing):
                device.restarting = False
                device.erased = None
            # self.quarantine(failed)
            # reset devices again to only the ones that succeeded
            _devices = self.findall(erased)
        elif erased:
            self.log.info("all devices were successfully erased!")

        for device in _devices:
            device.erased = datetime.now()

        self.task.add('restart', erased)
        self.stop(reason='restart')

        self.log.debug("devices after erase: "
                      "{0}".format([str(d) for d in _devices]))
        return _devices
    
    def prepare(self, devices):
        if self.stopped:
            raise StoppedError("enrollment was stopped")
        
        if devices:
            _available = self.available()
            for device in devices:
                if device not in _available:
                    self.log.error("cannot prepare unavailable device")

        if not devices:
            devices = self.available()

        ecids = self.task.prepare(only=[d.ecid for d in devices])

        # no ecids are making it here
        if not ecids:
            self.log.info("no devices need to be enrolled")
            return devices

        self.check_network(self.findall(ecids))
    
        self.log.info("enrolling devices: {0}".format(ecids))

        prepared = []
        failed = []
        try:
            prepared, missing = cfgutil.prepareDEP(ecids, log=self.log)
            self.task.installapps(prepared)
        except cfgutil.CfgutilError as e:
            self.log.error("prepare failed: {0}".format(e))
            if "must be erased" in e.message:
                self.task.erase(e.affected)
                self.task.prepare(e.unaffected)
            elif e.detail == "Network communication error.":
                self.task.prepare(e.unaffected)
            else:
                self.quarantine(ecids)
        except:
            self.log.error("prepare: UNKNOWN ERROR")
            raise

        if not prepared:
            self.log.error("no devices were prepared")
            return []
        
        if missing:
            self.log.error("enrollment failed on: {0}".format(missing))
            self.quarantine(missing)
        else:
            self.log.debug("all devices were successfully enrolled!")

        _devices = self.findall(prepared)
        for device in _devices:
            device.enrolled = datetime.now()
        self.set_background(_devices, 'alert')
        self.log.info("enrolled devices: "
                      "{0}".format([str(d) for d in _devices]))
        return _devices

    def installapps(self, devices):
        if self.stopped:
            raise StoppedError("no apps were installed")

        if not devices:
            devices = self.available()

        # get the ECIDs of the devices tasked for app installation
        ecids = self.task.installapps(only=[d.ecid for d in devices])

        if not ecids:
            self.log.info("no apps need to be installed")
            return devices

        self.log.info("installing apps on devices: "
                      "{0}".format([str(d) for d in devices]))

        devices = self.findall(ecids)
        for _devices, apps in self.apps.breakdown(devices):
            # would like to switch ACAdapter to use ecids (eventually)
            udids = [d.udid for d in _devices]
            try:
                adapter.install_vpp_apps(udids, apps, skip=True, wait=True)
                for d in _devices:
                    # not sure if this will work by default with properties
                    # device.apps += apps
                    # this should work (even if it's sloppy)
                    current = d.apps
                    d.apps = current + apps

            except adapter.ACAdapterError as e:
                self.log.error(e)
                raise e
        # self.set_background(devices, 'background')
        return devices
        


        
    def clearactivation(self, devices):
        raise Error("unable to clear activation")

    def activationLocked(self, devices):
        # technically we could check for installed apps and if
        # any of the apps aren't in the deployed app list, we have
        # a possible activation lock.
        
        # activation state might be the other key worth checking
        # cloudBackupsAreEnabled is the key we can look for
        # if it's defined, the system has been logged into with an
        # appleID (even if it's false)
        return False
        
    def authorization(self):
        '''Uses the directory specified to work out the private key
        and certificate files used for cfgutil
        returns ACAuthentication object
        '''
        if not self._auth:
            if not self._supervision:
                raise Error("no supervision directory")
            self._auth = self._cfgutil_auth(self._supervision)
        return self._auth

    def _cfgutil_auth(self, dir):
        '''Uses the directory specified to work out the private key
        and certificate files used for cfgutil
        returns ACAuthentication object
        '''
        self.log.debug("getting authorization for cfgutil")

        if not os.path.isdir(dir):
            err = "no such directory: {0}".format(dir)
            self.log.error(err)
            raise Error(err)

        for item in os.listdir(dir):
            file = os.path.join(dir, item)
            if item.endswith('.crt'):
                cert = file
            elif item.endswith('.key'):
                key = file
    
        # self.log.debug("CERT: {0}".format(cert))
        # self.log.debug("KEY: {0}".format(key))
    
        return cfgutil.Authentication(cert, key, self.log)    

    def set_background(self, devices, type):
        '''needs to be re-adapted to new layout
        '''
        # IDEA: another class for listing types of devices
        # self.devices.connected
        if not devices:
            return

        if not self._images:
            self.log.error("no images availalbe")
            return
        
        # can only set backgrounds for supervised devices
        
        ecids = [d.ecid for d in devices if d.enrolled]
        if not ecids:
            if devices:
                self.log.debug("can't ajust background on"
                               " non-supervised devices")
            self.log.debug("no backgrounds modified")
            return

        images = {}
        for file in os.listdir(self._images):
            name, ext = os.path.splitext(file)
            if ext in ['.png','.jpeg','.jpg']:            
                path = os.path.join(self._images, file)
                images[name] = path
        
        args = ['--screen', 'both']
        try:
            image = images[type]
            auth = self.authorization()
            succeeded, missing = cfgutil.wallpaper(ecids, image, args, 
                                                    auth, log=self.log)
            for device in self.findall(succeeded):
                device.background = type
        except cfgutil.CfgutilError as e:
            self.log.error("failed to set background: {0}".format(e))
            self.log.debug("unaffected: {0}".format(e.unaffected))
            self.log.debug("affected: {0}".format(e.affected))
        except KeyError as e:
            self.log.error("no image for: {0}".format(e))
            return
                

    def remove_temporary_profiles(self, udids):
        '''Currently unused
        remove any configuration profiles that start with 'tmp'
        Designed to remove the WiFi profile installed with the blueprint
        '''
        if not udids:
            self.log.debug("no UDIDs were specified")
            return
        
        self.log.info("checking for temporary configuration profiles")
        records = self.findall(udids)
        ecids = [r.read('ECID') for r in records]
        configProfiles = ['get', 'configurationProfiles']
        cfgoutput = cfgutil(self.log, ecids, configProfiles)

        for device in records:
            ecid = device.read('ECID')
            profiles = cfgoutput[ecid]
            if not profiles:
                err = "no profiles were found for device: {0}"
                self.log.error(err.format(device.name))
                # device should have the MDM profile
                device.failed('missing MDM profile')
                continue
            else:
                msg = "{0}: profiles: {1}".format(device.name, profiles)
                self.log.debug(msg)
        
            for profile in profiles['configurationProfiles']:
                pname = profile['displayName']
                # remove any profile that name starts with 'tmp'
                if pname.lower().startswith('tmp'):
                    self.log.info("removing profile: {0}".format(pname))
                    id = profile['identifier']
                    removal = ['remove-profile', id]
                    auth = self.authorization()
                    try:
                        cfgutil(self.log, [ecid], removal, auth)
                    except CfgutilError:
                        reason = 'removing temporary profile: {0}'
                        device.failed(reason.format(pname))
                else:
                    msg = "leaving profile installed: {0}".format(pname)
                    self.log.debug(msg)

    @property
    def stopped(self):
        return self.config.get('stopped', False)
    
    @stopped.setter
    def stopped(self, value):
        self.config.update({'stopped': value})

    def stop(self, reason=None):
        '''stops other manager instances from performing tasks
        '''
        # sync the TaskList
        # 
        self.stopped = True
        if reason:
            self.config.update({'reason':reason})
        self.log.error("STOPPED")
        raise StoppedError("Hold the press!")

    @property
    def locked(self):
        _locked = []
        _backgrounds = []
        # verify devices are still locked?
        previous = self.config.get('locked', [])
        # check the devices are still locked

        for device in self.findall():
            if device.locked:
                _locked.append(device)
                if device.background == 'background':
                    _backgrounds.append(device)
            else:
                if device.ecid in previous:
                    previous.remove(device.ecid)
                    self.config.update({'locked': previous})
                    
        if _backgrounds:
            self.set_background(_backgrounds, 'locked')

        if _locked:
            # empty the erase queue of locked devices
            self.task.erase(only=[d.ecid for d in _locked])

        return _locked        

    def lockdevices(self, ecids=[]):
        if not ecids:
            self.log.debug("no devices to lock")
            return
        devices = self.findall(ecids)
        self.log.debug("removing from erase: {0}".format(ecids))
        # empty the erase queue of locked devices
        self.task.erase(only=ecids)
        msg = "locking devices: {0}".format([str(d) for d in devices])
        self.slackbot.send(msg)
        self.log.error(msg)
        _backgrounds = []
        for device in devices:
            device.locked = datetime.now()
            if device.background != 'locked':
                _backgrounds.append(device)
        self.set_background(_backgrounds, 'locked')
        with self.config.lock.acquire():
            _locked = self.config.get('locked', [])
            self.config.update({'locked': _locked+ecids})
        
    @property
    def quarantined(self):
        _more = self.config.get('quarantine', [])
        if _more:
            self._quarantined = self._quarantined.union(_more)

        backgrounds = []
#         for device in self.findall(self._quarantined):
#             if device.background == 'background':
#                 backgrounds.append(device)
#         self.set_background(backgrounds, 'alert')
        return list(self._quarantined)

    def quarantine(self, ecids=[], task=None):
        if not ecids:
            self.log.debug("no devices to quarantine")
            return
        names = [str(d) for d in self.findall(ecids)]
        msg = "quarantining devices: {0}".format(names)
        self.slackbot.send(msg)
        self.log.error(msg)
        # quarantine is not persistant, I would like to change that
        self._quarantined = set(ecids).union(self.quarantined)
        self.config.update({'quarantine': list(self._quarantined)})
        _quarantined = self.findall(self._quarantined)
        self.set_background(_quarantined, 'alert')
        if task:
            self.task.add(task, list(self._quarantined))
        
    @property
    def ignored(self):
        '''TO-DO: clearer about whether ECIDs or devices are returned
        '''
        return self.quarantined + self.checkedout
    
    @property
    def verified(self):
        '''Placeholder for future verification 

        returns False (for now)
        
        because they system should be self healing, re-runs
        shouldn't do anything if everything is worked
        '''
        # deal with locked devices
        locked_ecids = self.locked
        for task in ['erase', 'installapps', 'prepare', 'restart']:
            removed = self.task.get(task, only=locked_ecids)
            if removed:
                msg = "{0}: removed locked: {1}".format(task, removed)
                self.log.debug(msg)

#         for device in self.findall(locked_ecids):            
#             self.task.query('installedApps', [device.ecid])

        # unlocked = self.findall(exclude=locked_ecids)
        try:
            config.FileLock('/tmp/ipad-restart.lock').acquire(timeout=0)
        except config.TimeoutError:
            self.log.debug("restarting... skipping verification")
            return True
            
        devicelist = self.devicelist()

        available = self.available(ecids=True)
        for device in self.findall(exclude=available):
            if not device.checkout or device.checkout < device.checkin:                
                name = device.name
                self.log.error("{0}: incorrect checkin".format(name))
        
        unavailable = self.unavailable(ecids=True)
        for device in self.findall(exclude=unavailable):
            if not device.checkin or device.checkout > device.checkin:                
                name = device.name
                self.log.error("{0}: incorrect checkout".format(name))
                
        

        for info in devicelist:
            ecid = info['ECID']
            device = self.device(ecid, info)
            if not device.serialnumber:
                self.task.query('serialNumber', [ecid])

            # check erase
            eraselist = self.task.list('erase', exclude=self.locked)
            if not device.erased and ecid not in eraselist:
                if ecid not in self.locked:
                    self.task.erase([ecid])
                
            
            if device.erased:
                if device.erased < device.checkin:
                    pass
            
            if not device.enrolled:
                pass
        return False
        
    def finalize(self, devices):
        '''Placeholder for finalization steps
        '''
        unlocked = [d for d in devices if not d.locked]
        _devices = [d for d in unlocked if d.background != 'background']
        if _devices:
            self.set_background(_devices, 'background')
            
    
    def verify(self):
        '''Placeholder for verfication steps
        run() should be harmless in the event of zero tasks
        '''
        with self.lock.acquire(timeout=-1):
            last_run = self.config.get('finished')
            if last_run:
                _seconds = (datetime.now() - last_run).seconds
                if _seconds < 60:
                    self.log.debug("ran less than 1 minute ago...")
                    return
        self.log.debug("verifying devices")
        if not self.verified:
            self.run()

    def run(self, ecid=None):
        with self.lock.acquire(timeout=-1):
            # if ecid is tasked for restart, skip this run
            if ecid and ecid in self.task.list('restart'):
                msg = "{0}: restarting: skipping run".format(ecid)
                self.log.debug(msg)
                return
            
            if self.task.alldone():
                self.log.info("all tasks have been completed")
                self.config.update({'finished':datetime.now()})
                return
            else:
                self.log.debug("Need to perform the following:")
                for k,v in self.task.record.items():
                    if v:
                        self.log.debug("{0}: {1}".format(k,v))

            time.sleep(5)
            self.query()

            devices = self.available()
            names = [d.name for d in devices]
            self.log.debug("available: {0}".format(names))
            try:
                erased = self.erase(devices)
            except StoppedError:
                self.config.update({'finished':datetime.now()})
                return

            finished = []
            try:
                prepared = self.prepare(erased)
                finished = self.installapps(prepared)
            except StoppedError as e:
                self.log.error(e)
            finally:
                self.config.update({'finished':datetime.now()})
                if finished:
                    self.finalize(devices)
                if ecid:
                    # IDEA: could use the ecid to check if the
                    # script finished (might be tricky)
                    pass


if __name__ == '__main__':
    pass
