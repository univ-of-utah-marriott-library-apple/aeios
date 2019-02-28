# -*- coding: utf-8 -*-

import os
import logging
import time
import logging

from datetime import datetime, timedelta

import config
import reporting
import tethering

from tasklist import TaskList
from device import Device
from appmanager import AppManager
from actools import adapter, cfgutil

'''Collection of tools for managing and automating iOS devices
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = ("Copyright (c) 2019 "
                 "University of Utah, Marriott Library")
__license__ = 'MIT'
__version__ = '2.5.5'
__url__ = None
__all__ = [
    'DeviceManager', 
    'Stopped',
    'DeviceList']

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

# 2.2.0:
#   - Major re-work
#   - query (renamed run_queries)
#   - @property; verified:
#       - Major changes
#       - now checks and re-tasks devices that:
#           - never checkedin
#           - never erased
#           - never enrolled
#           - are missing apps
#   - run():
#       - no longer passes devices along from erase(), to prepare(), to
#         installapps()
#       - all available devices are processed by each action
#   - finalize():
#       - modified to heavily rely upon verified
#       - checks for supervision
#       - modifies background images to reflect state of device
#       - no longer relies on returned devices
#       - always runs, unless stopped
#   - supervised():
#       - minor changes, might delete
#   - added find_new_apps():
#       - simple function imbedded in run_queries() to list and report
#         user installed apps
#   - updated for compatibility with device 2.0.3
#   - updated for compatibility with cfgutil 2.1.0
#       - run_queries adapted... needs testing
#       - erase adapted... needs testing
#       - prepare adapted.... needs testing
#       - set_background adapted... needs testing
#   - added additional comments
#   - added find_new_apps_callback (experimental)
#   - TO-DO: 
#       - tiered tasking:
#          - tasks hidden away and restored during finalize()
#       - add cfgutil():
#           - wrap cfgutil module for dryrun and testing
#       - error handling:
#           - cleanup erase, prepare, installapps with errorhandler
# 2.2.1:
#   - fixed minor errors
#   - incorporated changes from device: 2.4.0 
# 2.2.2:
#   - added exception handling for cfgutil.FatalError (2.2.0)
#   - trying to figure out why random errors started occurring on
#     iOS 12.1 cfgutil 2.7.1(444)
# 2.3.0:
#   - adaptations for tethering 1.3.0
#       - more forgiving when non-tethered devices attempt to enroll
#
# 2.4.0:
# - major re-work:
#   - devicelist -> list
#   - Added DeviceList():
#       - used to get various information from list of devices
#   - re-arranged some functions
#   - StoppedError -> Stopped
#   - changed various parts of control flow
# 2.4.1:
#   - bugs fixed:
#        __init__.reporting
#       replaced all instances of StoppedError with Stopped
#
# 2.5.0:
# major re-work:
#   - changed verification mechanism
#   - managed():
#       - reserved for future device management checking
#   - checkin():
#       - added managed() placeholder
#       - NOTE: still needs some work
#       - resets verified property
#       - run can be skipped (used by verify())
#   - erase():
#       - re-worked exception handling (needs to be tested)
#       - resets verified property
#   - supervise():
#       - fallback network mechanism (experimental)
#       - re-worked exception handling (needs to be tested)
#       - added query to only run on newly supervised devices
#       - resets verified property
#   - installapps():
#       - fallback network mechanism (experimental)
#       - re-worked exception handling (needs to be tested)
#       - added query to only run on devices with newly installed apps
#       - resets verified property
#   - set_background():
#       - slight modification of logic
#   - verified property:
#       - verification status persists between runs
#       - value in manager config
#       - moved previous functionality to _verify()
#   - (new) _verify():
#       - better checkin detection
#       - simplified supervision checking
#       - better app check:
#           - missing apps were not seen unless all apps were missing
#       - updates new verified property
#       - eliminated redundant checks
#       - better logging
#   - verify():
#       - now runs all pending queries before verification check
#       - no longer runs unnecessarily
#           - total verification negates re-run
#       - now checks for pending tasks
#       - run can be canceled manually
#   - finalize():
#       - removed redundant checks now found in verify()
#       - no longer queues queries
#       - no longer runs if Stopped
#       - better logic for settings device backgrounds
#   - run():
#       - simplified execution
#       - remove device argument
# 2.5.1:
#   - minor bug fixes

# 2.5.2:
#   - fixed mechanism for app reporting
#   - run_queries():
#       - isolated queries to only be performed on available devices
#       - fixed bug that consumed queries on unavailable devices
#       - fixed bug that erased installedApps if query wasn't present
#       - added modification to verified property if query is run
#   - added more logging:
#       - added log to reporter
#       - added clearer messages
#   - finalize():
#       - added missing call to verify()
#   - fixed bug where new apps would not be reported
#   - verify():
#       - added a stop check to exit early
#       - moved entire verification inside filelock
#   - _verify():
#       - added functionality to remove unnecessary tasks
#       - attempted to add mechanism to sanitize records of unavailable
#         devices, requires:
#           - slightly updated config [DONE]
#           - tasklist 2.1.1 [DONE]
#   - find_new_apps():
#       - slightly changed logic
#       - added better logging
#   - Modified Stopped(Exception):
#       - no longer has its own __init__
#       - no longer has reason property
#   - added _setup():
#       - necessary directories are now created during initialization
#       - removed similar functionality from __init__()
#   - minor string modifications
#   - waitFor():
#       - added wait keyword
#       - increased default wait time

# 2.5.3:
# minor bug fixes

# 2.5.4:
# - re-worked need_to_erase() and checkin
# - now allows for a grace period of 5 minutes for checkouts

# 2.5.5:
# - minor updates to verify()

# 2.5.6:
# - revamped device()

class Error(Exception):
    pass


class Stopped(Error):
    '''Exception to interrupt and signal to other DeviceManagers
    '''
    def __str__(self):
        return "STOPPED: " + str(self.message)


class DeviceList(list):
    '''convenience class for getting various properties of devices in
    a list
    '''    
    @property
    def ecids(self):
        return [x.ecid for x in self]
    
    @property
    def serialnumbers(self):
        return [x.serialnumber for x in self]
    
    @property
    def udids(self):
        return [x.udid for x in self]
    
    @property
    def names(self):
        return [x.name for x in self]

    @property
    def unsupervised(self):
        return DeviceList([x for x in self if not x.supervised])

    @property
    def supervised(self):
        return DeviceList([x for x in self if x.supervised])
    
    def __repr__(self):
        return "DeviceList({0})".format(self.names)


class CacheError(Error):
    pass


class Cache(object):

    def __init__(self, conf):
        self.devices = DeviceList()
        self.conf = conf
                
    @property
    def listed(self):
        return self.conf.get('Devices', [])

    @listed.setter
    def listed(self, value):
        self.conf.update({'Devices':value})
    
    def device(self, ecid):
        for d in self.devices:
            if ecid == d.ecid:
                return d
        raise CacheError("{0}: not in cache")
        
    def add(self, device):
        if device not in self.devices:
            self.devices.append(device)


class Resources(object):

    def __init__(self, root, directories):
        self.path = root
        for d in directories:
            path = os.path.join(root, d)
            setattr(self, d.lower(), path)
            if not os.path.isdir(path):
                os.mkdir(path)
    
    def __str__(self):
        return self.path
    
class DeviceManager(object):
    '''Class for managing multiple iOS devices
    '''
    def __init__(self, id='edu.utah.mlib.ipad', logger=None, **kwargs):
        if not logger:
            # create null logger if one wasn't specified
            logger = logging.getLogger(__name__)
            if not logger.handlers:
                logger.addHandler(logging.NullHandler())
        self.log = logger

        self.lock = config.FileLock('/tmp/ipadmanager', timeout=5)
        self.config = config.Manager("{0}.manager".format(id), **kwargs)
        self.file = self.config.file

        # paths to various resources
        resources = os.path.dirname(self.config.file)
        r = ['Devices', 'Supervision', 'Images', 'Profiles', 'Logs', 'Apps']
        self.resources = Resources(resources, r)
        self.images = self.resources.images
        self.profiles = self.resources.profiles
        self.supervision = self.resources.supervision
        self.logs = self.resources.logs
        self._devices = self.resources.devices
        
        # self.resources = os.path.dirname(self.config.file)
        # r = self._setup()
        # self._devicepath = r['Devices']
        # self.profiles = r['Profiles']
        # self.images = r['Images']
        # self.supervision = r['Supervision']
        # self.logs = r['Logs']

        try:
            self.config.read()
        except config.Error as e:
            self.log.error("unable to read config: {0!s}".format(e))
            self.config.write({'Reporting': {'Slack': {}},
                               'Devices': [],
                               'Idle': 300})

        self.cache = Cache(self.config)
        _path = str(self.resources)
        self.task = TaskList(id, path=resources, logger=self.log)
        self.apps = AppManager(id, path=resources, logger=self.log)

        self._lookup = self.config.get('Devices')
        self.idle = self.config.get('Idle')

        _reporting = self.config.get('Reporting', {'Slack': {}})
        self.log.debug("reporting: {0}".format(_reporting))
        self.report = reporting.reporterFromSettings(_reporting) 

        self._cfgutillog = os.path.join(self.logs, 'cfgexec.log')        

        self._auth = None

    # get rid of this if Resource works
    def _setup(self):
        '''Various validation of internal setup
        '''
        ## verify resource files and directories
        r = ['Devices', 'Supervision', 'Images', 'Profiles', 'Logs']
        defaults = {}
        for name in r:
            path = os.path.join(self.resources, name)
            defaults[name] = path
            if not os.path.isdir(path):
                os.mkdir(path)
            
        ## verify Accessibility access
        ## verify VPP account (if possible)
        return defaults

    @property
    def stopped(self):
        return self.config.get('Stopped', False)
    
    @stopped.setter
    def stopped(self, value):
        self.config.update({'Stopped': value})

    def stop(self, reason=None):
        '''stops other manager instances from performing tasks
        '''
        self.stopped = True
        if reason:
            self.config.update({'StopReason': reason})
        _reason = reason if reason else 'no reason specified'
        self.log.debug("stopping for {0}".format(_reason))
        raise Stopped(_reason)

    def managed(self, device):
        '''Placeholder for future management check
        Returns True (for now)
        '''
        return True

    def manage(self, device):
        '''Placeholder for adding device to automated tasks
        Does nothing for now
        '''
        pass
            
    def authorization(self):
        '''Uses the directory specified to work out the private key
        and certificate files used for cfgutil
        returns ACAuthentication object
        '''
        if not self._auth:
            self.log.debug("getting authorization for cfgutil")
            dir = self.supervision
        
            if not os.path.isdir(dir):
                err = "no such directory: {0}".format(dir)
                self.log.error(err)
                raise Error(err)

            for item in os.listdir(dir):
                file = os.path.join(dir, item)
                if item.endswith('.crt'):
                    cert = file
                elif item.endswith('.key') or item.endswith('.der'):
                    key = file
    
            self._auth = cfgutil.Authentication(cert, key, self.log)    
        return self._auth

    # I want to get rid of this
    def findall(self, ecids=None, exclude=[]):
        '''returns list of Device objects for specified ECIDs
        '''
        if ecids is None:
            ecids = []
            for file in os.listdir(self.resources.devices):
                #NOTE: would be better to identify files based on valid
                #      ECIDs, but this will work for now
                if 'DS_Store' in file:
                    continue
                if file.endswith('.plist'):
                    ecids.append(os.path.splitext(file)[0])

        try:
            devices = DeviceList([self.device(x) for x in ecids 
                                                  if x not in exclude])
        except:
            self.log.error("failed to find devices")
            self.log.debug("recovering...")
            # an error can be thrown if findall() is called before
            # a device record has been created
            devices = DeviceList()
            for i in self.list():
                if i['ECID'] in ecids and i['ECID'] not in exclude:
                    devices.append(self.device(i['ECID'], i))

        return devices

    def available(self):
        '''Returns list of all devices (or device ECID's) that are
        currently checked in
        '''
        devices = [self.device(x['ECID'], x) for x in self.list()]
        return DeviceList(devices)

    def supervised(self):
        '''Returns DeviceList() of currently supervised devices
        '''
        # verify supervision
        # - would require cached queries (TO-DO)
        pass

    def unsupervised(self):
        '''Returns DeviceList() of currently unsupervised devices
        '''
        # Inverse of self.supervised
        # - would require cached queries (TO-DO)
        pass

    def device(self, ecid, info={}):
        '''Returns Device object from ECID
        '''
        self.log.debug("cached devices: {0}".format(self.cache.devices))
        try:
            # return cached device object (if we have one)
            d = self.cache.device(ecid)
            self.log.debug("returning cached device: {0}".format(d))
            return self.cache.device(ecid)
        except CacheError:
            self.log.debug("couldn't find cached devices")
            pass
        
        self.log.debug("creating new device object: {0}".format(ecid))
        device = Device(ecid, info, path=self.resources.devices)
        self.cache.add(device)
        self.log.debug("cached device: {0}".format(device))
        # self._device[ecid] = device
        return device
                           
    def devices(self, ecids):
        return DeviceList([self.device(x) for x in ecids])
            
    # should be handled by the appmanager
    def find_new_apps(self, device):
        '''Returns list of apps the Appmanager to find new, user-installed applications
        '''
        # `cfgutil get installedApps`:
        #   provides a list of dicts using 4 keys: 
        #      ['itunesName', 'displayName', 
        #        'bundleIdentifier', 'bundleVersion']
        # apps are installed using 'itunesName', and 'displayName' 
        # is useful only when parsing GUI

        msg = "checking {0} for user-installed apps..."
        self.log.debug(msg.format(device.name))
        appnames = [app.get('itunesName') for app in device.apps]
            
        ## list of apps that aren't known to the Appmanager
        return self.apps.unknown(device, appnames)
    
    def list(self, refresh=False, timeout=30):        
        '''Returns list of attached devices using cfgutil.list() 
        list is cached and refreshed once every 30 seconds
        '''
        # keep listing down to once per 30 seconds (and first run)
        now = datetime.now()
        # set refresh to <timeout> seconds ago
        expires = now - timedelta(seconds=timeout)
        # default listed == refresh (triggering update)
        listed = self.config.setdefault('lastListed', expires)
        if refresh or listed <= expires:
            # update the cache and record the timestamp
            self.cache.listed = cfgutil.list()
            self.config.update({'lastListed': now})
        return self.cache.listed

    def need_to_erase(self, device, apps=None):
        '''Returns True if device needs to be erased
        I've had a lot of issues with false positives on device reset
        '''
        name = device.name
        self.log.debug("checking erase: {0}".format(name))

        # device is not managed (don't erase)
        if not self.managed(device):
            self.log.debug("{0}: not managed".format(name))
            return False
        
        # device is restarting (don't erase)
        if device.restarting:
            self.log.debug("{0}: restarting".format(name))
            return False
        
        # device has NEVER checked in (erase)
        if not device.checkin:
            self.log.debug("{0}: brand new device found!".format(name))
            return True

        # device has not been erased (erase)
        if not device.erased:
            self.log.debug("{0}: has never been erased".format(name))
            return True

        now = datetime.now()

        # device has been erased in the last 10 minutes (don't erase)
        was_erased = now - device.erased
        if was_erased < timedelta(minutes=10):
            _msg = "{0}: was erased less than 10 minutes ago..."
            self.log.debug(_msg.format(name))
            self.verified = False
            return False
        else:
            self.log.debug("{0}: erase timeout expired".format(name))
        
        ## This is where things get messy
        #  
        try:
            # if the device has been checked out since last checkin
            if device.checkout > device.checkin:
                # see if checkout happened less than 5 minutes ago
                self.log.debug("{0}: was checked out".format(name))
                time_away = now - device.checkout
                _msg = "{0}: checkout: {1!s} minutes"
                self.log.debug(_msg.format(name, time_away))
                if time_away > timedelta(minutes=5):
                    self.log.debug("{0}: valid checkout".format(name))
                    return True
                else:
                    # reset checkout to 1 minute before last checkin
                    self.log.debug("{0}: invalid checkout".format(name))
                    recover = device.checkin - timedelta(minutes=1)
                    _msg = "{0}: adjusting checkout time: {1}"
                    self.log.debug(_msg.format(name, recover))
                    device.checkout = recover
                    self.log.debug("invalidating verification")
                    self.verified = False
            else:
                self.log.debug("{0}: not checked out".format(name))
        except TypeError:
            self.log.debug("{0}: never checked out".format(name))
            # create dummy checkout 1 minute before checkin
            device.checkout = device.checkin - timedelta(minutes=1)
        
        return False        

    def check_network(self, devices, tethered=True):    
        # TO-DO: this needs to be tested to see that if tethering fails
        #        a wi-fi profile is used instead
        _use_tethering = tethered
        if _use_tethering and not tethering.enabled(log=self.log):
            self.log.info("Device Tethering isn't enabled...")
            try:
                tethering.restart(timeout=30)
            except tethering.Error as e:
                self.log.error(e)
                _use_tethering = False
            except Exception as e:
                self.log.error("check_network: unexpected error occurred: {0!s}".format(e))
                raise e

        if _use_tethering:
            self.log.debug("using tethering")
            sns = devices.serialnumbers
            tethered = tethering.devices_are_tethered(sns)
            timeout = datetime.now() + timedelta(seconds=10)

            while not tethered:
                time.sleep(5)
                tethered = tethering.devices_are_tethered(sns)
                if datetime.now() > timeout:
                    self.log.error("timed out waiting for devices")
                    break
                
            if not tethered:
                try:
                    # this will have to be removed eventually
                    tethering.restart(timeout=10)
                    return
                except tethering.Error as e:
                    self.log.error(e)
                    raise
        else:
            # too hidden for my liking, but whatever
            self.log.debug("using wifi profile")
            wifi = os.path.join(self.profiles, 'wifi.mobileconfig')
            cfgutil.install_wifi_profile(devices.ecids, wifi, 
                                    log=self.log, file=self._cfgutillog)
            time.sleep(2)

    def checkin(self, info, run=True):
        '''process of device attaching
        '''
        device = self.device(info['ECID'], info)
        
        ## Pre-checkin
        
        #TO-DO:
        # validate checkin (currently done by need_to_erase())
        # - invalid:
        #       unmanaged, restarting, 
        
        # append the ECID to the name for logging
        if device.name.startswith('iPad'):
            # e.g. 'iPad (0x00000000001)'
            name = "{0} ({1})".format(device.name, device.ecid)
        else:
            name = device.name
        
        if not self.managed(device):
            #TO-DO: add mechanism to prompt for device management
            self.log.info("{0}: ignoring unmanaged device".format(name))
            return
        else:
            self.log.debug("{0}: device is managed".format(name))
        
        if self.stopped:
            # mechanism to stall while devices restart
            
            # old:
            # self.waitfor(device, 'restart')
            
            # untested:
            if device.restarting:
                self.waitfor(device, 'restart')
                device.restarting = False
        
        
        ## Determine actions need to be taken
        if self.need_to_erase(device):
            self.log.debug("{0}: will be erased".format(name))
            self.task.erase([device.ecid])
            self.task.query('installedApps', [device.ecid])
        else:
            self.log.debug("{0}: will NOT be erased".format(name))
        
        # at this point all checks have been made and 
        # device.restarting = False
        device.checkin = datetime.now()
        
        if run:
            self.run()

    def checkout(self, info):
        '''saves timestamp of device checkout (if not restarting)
        '''
        device = self.device(info['ECID'], info)
        # IDEA: could just return if self.stopped (would eliminate need 
        #       for device restart tracking)

        # skip checkout if device has been marked for restart
        if device.restarting:
            self.log.info("{0}: restarting...".format(device.name))
            #device.restarting = False
        else:
            self.log.info("{0}: checked out".format(device.name))            
            device.checkout = datetime.now()
            device.verified = False

    def waitfor(self, device, reason, wait=120):
        '''Placeholder for waiting for restart
        '''
        _reason = 'StopReason'
        # if stopped, but we don't have a reason
        if self.stopped and not self.config.get(_reason):
            self.log.debug("stopped for no reason...")
            self.stopped = False
            return

        self.log.debug("instructed to wait for: {0}".format(reason))
        if reason != self.config.get(_reason):
            raise Stopped("not stopped for: {0}".format(reason))

        # get this device's ecid out of the queue (if it's there)
        self.task.get(reason, only=[device.ecid])
        device.restarting = False

        ## this should block all devices until the stopped reason
        ## has passed
        self.log.debug("waiting for: {0}".format(reason))
        lockfile = '/tmp/ipad-{0}.lock'.format(reason)
        lock = config.FileLock(lockfile)
        with lock.acquire(timeout=-1):
            waiting = self.task.list(reason)
            if not waiting:                
                if self.stopped and self.config.get(_reason):
                    self.stopped = False
                    self.config.delete(_reason)
                return

            stoptime = datetime.now() + timedelta(seconds=wait)
            while waiting:
                time.sleep(5)
                msg = "waiting on {0}: {1}".format(reason, waiting)
                self.log.debug(msg)
                waiting = self.task.list(reason)
                if datetime.now() > stoptime:
                    ecids = self.task.get(reason)
                    self.log.debug("gave up waiting")
                    break                            
            self.stopped = False
            self.config.delete(_reason)

    def run_queries(self):
        '''runs tasked queries using cfgutil

        '''
        self.log.info("running device queries...")
        if not self.task.queries():
            self.log.info("no queries to perform")
            return
        
        available = self.available().ecids
        ## Temporary cache of existing queries
        _cache, ecidset = {}, set()
        # merge all of the queries into one 
        for q in self.task.queries():
            # empty the query of all ECIDs (preserved in _cache)
            ecids = self.task.query(q, only=available)
            if ecids:
                _cache[q] = ecids
                # create a set of all unique ECIDs
                ecidset.update(_cache[q])

        if not _cache:
            self.log.debug("no queries for available devices")
            return

        # list of all keys for cfgutil.get()
        queries = _cache.keys()
        self.log.debug("queries: {0}: {1}".format(queries, ecidset))
        try:
            self.verified = False
            self.log.debug("{0}: {1}".format(queries, ecidset))
            result = cfgutil.get(queries, ecidset, log=self.log, 
                                 file=self._cfgutillog)
            self.log.debug("result: {0}".format(result._output))
        except Exception as e:
            self.log.error(str(e))
            for q,ecids in _cache.items():
                msg = 're-building queries: {0}: {1}'.format(q, ecids)
                self.log.debug(msg)
                self.task.query(q, ecids)
            raise
        
        ## Process results

        # all devices that were specified in the combined query
        for device in self.devices(ecidset):
            # get all information returned for this device
            info = result.get(device.ecid, {})
            if info:
                # iterate the cache to find queries for this device
                for q,ecids in _cache.items():
                    # NOTE: may only update the key that was queried
                    #       ... might be beneficial to update all keys?
                    #       ... would be side effect...
                    if device.ecid in ecids:
                        # get the value of the query result
                        v = info.get(q)
                        if v is not None:
                            device.update(q, v)
                            # remove successful queries from the cache
                            ecids.remove(device.ecid)
                        else:
                            err = "missing query result: {0}: {1}"
                            self.log.error(err.format(q, device.name))

                # TO-DO: should be handled elsewhere and not buried here
                if q == 'installedApps':
                    # find and report any unknown apps
                    userapps = self.find_new_apps(device)
                    # only report if new apps were found
                    if userapps:
                        # TO-DO: design mechanism for tracking repeat installations
                        smsg = "new user apps: {0}".format(userapps)
                        msg = "NEW: {0}: {1}".format(device.name, smsg)
                        self.log.info(msg)
                        self.report.send(msg)
                    else:
                        _msg = "{0}: no unknown apps found"
                        self.log.debug(_msg.format(device.name))

                
            else:
                err = "no results returned for device: {0}"
                self.log.error(err.format(device.name))

        # cache should only be made up of failed (or un-run)
        # queries at this point
        # TO-DO: test cache removes successful queries
        for q,ecids in _cache.items():
            if ecids:
                msg = "run_queries: re-tasking query: {0}: {1}"
                self.log.debug(msg.format(q, ecids))
                self.task.query(q, ecids)

        # forward along the results for processing elsewhere
        return result

    def erase(self, targets):
        '''Erase specified devices and mark them for preparation
        '''
        # get subset of device ECIDs that need to be erased
        tasked_ecids = self.task.erase(only=targets.ecids)

        if not tasked_ecids:
            self.log.info("no devices need to be erased")
            return

        ## EXTRA LOGGING: (doesn't really do anything)
        _missing = self.task.list('erase')
        if _missing:
            names = self.devices(_missing).names
            self.log.error("missing devices tasked for erase")
            self.log.debug("missing: {0}".format(names))

        # update device record before erase (or will count as checkout)
        tasked = self.devices(tasked_ecids)
        for device in tasked:
            self.log.debug("erase: found device: {0}".format(device.name))
            device.restarting = True
            device.delete('erased')
    
        erased = []
        failed = []
        try: 
            self.verified = False
            self.log.info("erasing devices: {0}".format(tasked))
            result = cfgutil.erase(tasked.ecids, log=self.log, 
                                   file=self._cfgutillog)
            erased = self.devices(result.ecids)
            failed = self.devices(result.missing)

        except cfgutil.FatalError as e:
            # no device was erased
            self.log.debug("erase: fatal error occurred")
            self.log.error(str(e))
            if "complete the activation process" in e.message:
                # handle devices that are activation locked
                _locked = self.devices(e.affected)
                err = "activiation locked: {0}".format(_locked.names)
                self.log.error(err)
                self.report.send(err)
                # TO-DO: still need a way of separating these systems
            raise e

        except cfgutil.CfgutilError as e:
            # some devices were erased (continue with working devices)
            self.log.error("partial erase failure: {0}".format(e))
            erased = self.devices(e.unaffected)
            failed = self.devices(e.affected)
            self.log.debug("unaffected devices: {0}".format(erased))
            self.log.error("affected devices: {0}".format(failed))

        finally:
            # if nothing was erased, then everything failed
                
            if not erased:
                self.log.error("erased failed for all devices")
                self.log.debug("failed devices: {0}".format(tasked))
                failed = tasked
                
            if failed:
                names = failed.names
                self.log.error("erase failed: {0}".format(names))
                self.task.erase(failed.ecids)
                self.log.debug("re-tasked: {0!s}".format(failed))
                # unmark failed devices as restarting
                for d in devices:
                    d.restarting = False
            else:
                self.log.debug("all devices were successfully erased!")

            if erased:
                msg = "succesfully erased: {0}".format(erased.names)
                self.log.info(msg)     
                ## process erased devices
                # task devices for supervision and app installation
                self.task.prepare(erased.ecids)
                self.task.installapps(erased.ecids)
        
                now = datetime.now()
                for device in erased:
                    device.erased = now

                self.task.add('restart', erased.ecids)
        
        self.stop(reason='restart')
    
    def supervise(self, targets):
        '''All encompassing supervision
        devices are stripped down to unsupervised
        '''
        ## Check if manager has been stopped
        if self.stopped:
            raise Stopped("device supervision was stopped")

        # only continue with unsupervised devices
        unsupervised = targets.unsupervised
        tasked_ecids = self.task.prepare(only=unsupervised.ecids)                

        if not tasked_ecids:
            self.log.info("no devices need to be supervised")
            return

        ## EXTRA LOGGING: (doesn't really do anything)
        _missing = self.task.list('prepare')
        if _missing:
            names = self.devices(_missing).names
            self.log.error("missing devices tasked for preparation")
            self.log.debug("supervise: missing: {0}".format(names))

        # make sure device network checks out
        tasked = self.devices(tasked_ecids)
        try:
            self.check_network(tasked, tethered=True)
        except tethering.Error as e:
            self.log.error("network error: {0!s}".format(e))
            self.check_network(tasked, tethered=False)
    
        prepared, failed = [], []
        try:
            self.log.info("preparing devices: {0}".format(tasked.names))
            self.verified = False
            result = cfgutil.prepareDEP(tasked.ecids, log=self.log, 
                                        file=self._cfgutillog)
            prepared = self.devices(result.ecids)
            failed = self.devices(result.missing)

        except cfgutil.CfgutilError as e:
            err = "supervision partially failed: {0!s}".format(e)
            self.log.error(err)
            prepared = self.devices(e.unaffected)
            failed = self.devices(e.affected)

        except cfgutil.FatalError as e:
            self.log.error("supervision failed: {0!s}".format(e))
            if "must be erased" in e.message:
                err = "erroneously attempted to re-supervise device(s)"
                self.log.error(err)
            elif e.detail == "Network communication error.":
                self.log.error("Network unavailable")
            else:
                # put everything back into the queue
                self.log.debug("unexpected fatal error")
                self.log.error(e.detail)

            # debating whether or not the exception should be raised
            # raise e

        except Exception as e:
            err = "supervise: unexpected error: {0!s}".format(e)
            self.log.error(err)
            raise e

        finally:
            # re-query supervision for ALL devices
            self.task.query('isSupervised', tasked.ecids)
            # any devices that remain unsupervised will be re-tasked
            #   during verification
            if prepared:
                names = prepared.names
                msg = "successfully prepared: {0}".format(names)
                self.log.info(msg)
                for device in prepared:
                    ## not sure this is being used anymore
                    device.enrolled = datetime.now()
                    device.supervised = True
                
                ## this may also be unnecessary
                # self.set_background(prepared, 'alert')

                #EXPERIMENTAL: 
                self.restart(prepared)

            else:
                self.log.error("no devices were supervised")
            
    def restart(self, devices):
        for device in devices:
            device.restarting = True
        # self.task.add('restart', devices.ecids)
        _auth = self.authorization()
        result = cfgutil.cfgutil('restart', devices.ecids, auth=_auth,
                                 log=self.log, file=self._cfgutillog)    
        self.stop(reason='restart')

    def _installapps(self, devices, check=True):
        '''Hack to install apps from local .ipa files
        currently there is no mechanism to store .ipa files
        nor do I have any immediate plans to support or 
        '''
        if check:
            if self.stopped:
                raise Stopped("skipped app installation")

            tasked_ecids = self.task.installapps(only=devices.ecids)
            if not tasked_ecids:
                self.log.info("no apps need to be installed")
                return
            tasked = self.devices(tasked_ecids)
        else:
            tasked = devices

        path = self.resources.apps
        appfiles = [os.path.join(path, x) for x in os.listdir(path)]
        
        try:
            result = cfgutil.cfgutil('install-apps', tasked.ecids, 
                                     appfiles, file=self._cfgutillog,
                                     log=self.log)
        except cfgutil.Error as e:
            self.log.error(str(e))
        
    def installapps(self, targets):
        ## Check if manager has been stopped
        if self.stopped:
            raise Stopped("skipped app installation")

        # get the ECIDs of the devices tasked for app installation
        tasked_ecids = self.task.installapps(only=targets.ecids)
        if not tasked_ecids:
            self.log.info("no apps need to be installed")
            return

        ## EXTRA LOGGING: (doesn't really do anything)
        _missing = self.task.list('installapps')
        if _missing:
            names = self.devices(_missing).names
            self.log.error("missing devices for app installation")
            self.log.debug("missing: {0}".format(names))

        tasked = self.devices(tasked_ecids)
        self._installapps(tasked, check=False)
        #TO-DO:
        # - add mechanism to record repeated errors
        # - spawn process that captures downloaded apps
        self.log.info("installing apps: {0}".format(tasked.names))
        for _devices, apps in self.apps.breakdown(tasked):
            self.verified = False
            # would like to switch ACAdapter to use ecids (eventually)
            udids = _devices.udids
            try:
                self.log.info("{0} installing {1}".format(udids, apps))
                adapter.install_vpp_apps(udids, apps, skip=True, 
                                         wait=True)
                #TO-DO: 
                #   - mechanism that clears all recorded errors
                
            except adapter.ACAdapterError as e:
                # this is not being raised with the skip=True
                self.log.error(e)
                self.log.debug("installapps: error str: {0!e}".format(e))
                self.log.debug("installapps: e.message: {0}".format(e.message))
                raise e
            except Exception as e:
                err = "installapps: unexpected error: {0!s}".format(e)
                self.log.error(e)
                self.log.debug("installapps: error str: {0!s}".format(e))
                self.log.debug("installapps: e.message: {0}".format(e.message))
                raise e
            finally:
                self.task.query('installedApps', tasked.ecids)
        
    def set_background(self, targets, _type):
        '''set the background of the specified devices
        '''
        if self.stopped:
            raise Stopped("skipping wallpaper")

        if not targets:
            self.log.error("background: no devices specfied")
            return

        if not self.images:
            self.log.error("no images available")
            return

        # background cannot be set on unsupervised devices
        ecids = targets.supervised.ecids
        if not ecids:
            self.log.info("no wallpapers modified")
            return

        images = {}
        for file in os.listdir(self.images):
            name, ext = os.path.splitext(file)
            if ext in ['.png','.jpeg','.jpg']:            
                path = os.path.join(self.images, file)
                images[name] = path
        
        args = ['--screen', 'both']
        try:
            image = images[_type]
            auth = self.authorization()
            result = cfgutil.wallpaper(ecids, image, args, auth, 
                                 log=self.log, file=self._cfgutillog)
            for device in self.devices(result.ecids):
                device.background = _type
        except cfgutil.CfgutilError as e:
            self.log.error("failed to set background: {0}".format(e))
            self.log.debug("unaffected: {0}".format(e.unaffected))
            self.log.debug("affected: {0}".format(e.affected))
        except KeyError as e:
            self.log.error("no image for: {0}".format(e))
            return

    @property
    def verified(self):
        '''Check if verification has been completed
        (reset by checkin, checkout, erase, supervise, and installapps)
        '''
        return self.config.setdefault('verified', False)

    @verified.setter
    def verified(self, value):        
        if not isinstance(value, bool):
            raise TypeError("{0}: not boolean".format(value))
        self.config.update({'verified': value})

    def _verify(self):
        '''Current verification mechanism, but is somewhat hidden:
        >>> if not self.verified:
        >>>     # do something
        
        NOTE: I would like to change this in the future, but should work
              relatively well for now 
        '''
        self.log.debug("running significant verification")
                    
        _tasks = {}
        _verified = True
        # get list of all currently connected devices
        device_list = self.list()
        
        # list of available ECIDs 
        # available_ecids = [x['ECID'] for x in device_list]
        available_ecids = self.available().ecids
        ## Get updated list of installed apps
        self.log.debug("_verify: refreshing installed apps")
        self.task.query('installedApps', available_ecids)
        self.run_queries()
        
        
        for info in device_list:
            # create a device object
            device = self.device(info['ECID'], info)
            
            self.log.info("verifying: {0}".format(device.name))

            ## Verify device Serial Number
            if not device.serialnumber:
                self.log.error('  serial number: missing...')
                self.task.query('serialNumber', [device.ecid])
            else:
                self.log.info('   serial number: good!')

            ## Verify device Checkin
            if not device.checkin:
                self.log.error("        checkin: missing...")
                self.log.debug(" ... skipping additional verification")
                _verified = False
                # this leads down a rabbit hole that may need to be 
                # re-looked at
                self.checkin(info, run=False)
                continue
            else:
                self.log.info("         checkin: succeeded!")


            ## Verify device was erased
            if not device.erased:
                self.log.error("          erase: failed...")
                self.log.debug(" ... skipping additional verification")
                _verified = False
                _erasetask = _tasks.setdefault('erase', [])
                _erasetask.append(device.ecid)
                continue
            else:
                self.log.info("           erase: succeeded!")
            

            ## Verify device is supervised
            if not device.supervised:
                _enrolltask = _tasks.setdefault('prepare', [])
                _enrolltask.append(device.ecid)
                self.log.error("    supervision: failed...")
            else:
                self.log.info("     supervision: succeeded!")
                # remove ecid from task (if present)
                self.task.prepare(only=[device.ecid])
                   
                                
            ## Verify all Apps were installed
            app_set = set(self.apps.list(device))
            if app_set:
                if device.apps:
                    installed = [x['itunesName'] for x in device.apps]
                    # list of any apps that are missing
                    missing = list(app_set.difference(installed))
                else:
                    # all apps are missing
                    missing = list(app_set)

                if missing:
                    # some or all of apps are missing from the device
                    _apptask = _tasks.setdefault('installapps', [])
                    _apptask.append(device.ecid)               
                    self.log.error("           apps: missing...")
                    self.log.debug("missing apps: {0}".format(missing))
                else:
                    self.log.info("            apps: installed!")
                    # remove ecid from task (if present)
                    self.task.installapps(only=[device.ecid])
                    
            else:
                self.log.info("            apps: N/A")
        
        # TO-DO: this doesn't seem to be working... but isn't breaking
        #        anything either
        # NOTE:  probably don't need to fail verification

        ## Check unavailable devices        
        remove_pending = []
        for device in self.findall(exclude=available_ecids):
            # skip restarting devices
            if device.restarting:
                continue

            # sanitize unavailable device records
            remove_pending.append(device.ecid)

            if not device.checkout:
                self.log.error("device was never checked out")
                device.checkout = datetime.now()
                #self.task.remove([device.ecid], all=True)
        
        ## remove all pending tasks and queries for missing devices
        if remove_pending:
            self.log.debug("removing task for unavailable devices")
            self.task.remove(remove_pending, all=True)

        ## Re-task anything that failed verification
        self.log.debug("ALL RETASK ITEMS: {0}".format(_tasks))
        for name,ecids in _tasks.items():
            # if any tasks have to be added then verification failed
            _verified = False
            self.task.add(name, ecids, exclude=remove_pending)
            _added = [set(ecids) - set(remove_pending)]
            msg = "_verify: retasked: {0}: {1}"
            self.log.debug(msg.format(name, _added))
        
        self.log.debug("_verify: status: {0}".format(_verified))
            
        return _verified
        
    def verify(self, run=False):
        '''Simple verification
        runs more significant verification if any queries were run
        '''
        with self.lock.acquire(timeout=-1):
            if self.stopped:
                self.log.info("verify was stopped")
                return

            # TO-DO: fix for adjusted idle timing
            last_run = self.config.get('finished')
            if last_run:
                _seconds = (datetime.now() - last_run).seconds
                if _seconds < 60:
                    self.log.debug("ran less than 1 minute ago...")
                    return

            self.log.info("verifying devices... ")

            # - backgrounds? (not in _verify)
            # - erase? verifier object erase(expected apps)
            # - check recursion (below)

            ## Run queries (resets verification if necessary)
            self.log.debug("verify: running queries")
            self.run_queries()

            ## Check all tasks have been completed
            # NOTE: can return false positives if unavailable devices
            #       are tasked
            # TO-DO: fix unavailable device records in _verify()
            self.log.debug("verify: checking for pending tasks...")
            tasks_pending = False
            for k in ['erase', 'prepare', 'installapps']:
                _ecids = self.task.list(k)
                _msg = "verify: pending task: {0}: {1}"
                self.log.debug(_msg.format(k, _ecids))
                if _ecids:
                    tasks_pending = True

            if tasks_pending:
                self.log.info("verify: pending tasks found")
                self.verified = False
            else:
                self.log.info("verify: no pending tasks")

            ## Check verification status
            if not self.verified:
                self.verified = self._verify()

        
            # re-check verification
            if not self.verified:
                self.log.info("verification failed...")
                if run:
                    self.run()
            else:
                self.log.info("all devices and tasks were verified!")

    def finalize(self):
        '''Redundant finalization checks, verify tasks completed, 
        and adjust backgrounds of supervised devices
        '''
        self.log.debug("finalizing devices")
        if self.stopped:
            # self.config.update({'finished':datetime.now()})
            raise Stopped("finalization stopped")

        # run verification
        self.verify()
        
        ## Check tasks for any re-tasked devices
        _retasked = set()
        if not self.verified:
            for k,v in self.task.record.items():
                if v:
                    _retasked.update(v)
                    self.log.debug("retasked: {0}: {1}".format(k,v))
        
        _wallpapers = {'alert': DeviceList(), 
                       'background': DeviceList()}

        devices = self.available()
        ## Find devices that need wallpaper
        for d in devices:
            if d.ecid in _retasked:
                if d.background != 'alert':
                    _wallpapers['alert'].append(d)
            elif d.background != 'background':
                _wallpapers['background'].append(d)

        err = "unable to set background: {0}: {1!s}"
        for image, _devices in _wallpapers.items():
            if _devices:
                try:
                    self.set_background(_devices, image)
                except cfgutil.Error as e:
                    self.log.error(err.format(image, e))
        
        # update finishing timestamp            
        self.config.update({'finished':datetime.now()})
        self.log.debug("finalization complete")
      
    def run(self):
        # keep multiple managers from running simultaneously
        #   (will be changed in future version)
        self.log.info("running automation")
        with self.lock.acquire(timeout=-1):
            if self.stopped:
                self.log.debug("run stopped")
                return
            
            if self.task.alldone() and self.verified:
                self.log.info("all tasks have been completed")
                self.finalize()
                # exit early if no tasks exist
                return
            else:
                # log all tasks by name and ECIDs
                self.log.info("Agenda:")
                for k,v in self.task.record.items():
                    if v:
                        # only print tasks that are on the agenda
                        self.log.info("{0}: {1}".format(k,v))

            # give lagging devices a chance to catch up
            time.sleep(5)
            self.run_queries()

            devices = self.available()
            self.log.debug("available: {0}".format(devices.names))
    

            ## Pre-Erase actions

            ## Erase devices
            try:
                self.erase(devices)
            except Stopped as e:
                self.log.info(e)
                return

            ## Prepare devices (least critical step w/ DEP)
            try:
                self.supervise(devices)
            except Stopped as e:
                self.log.info(e)
                return
            
            try:
                self.installapps(devices)
            except Stopped as e:
                self.log.info(e)
                return
            except adapter.ACAdapterError as e:
                self.log.error(str(e))

            self.finalize()
            self.log.info("run finished")

def main():
    print("hello world")

if __name__ == '__main__':
    main()
