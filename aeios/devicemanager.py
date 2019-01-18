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
__version__ = '2.5.2'
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
    def ecids(self):
        return [x.ecid for x in self]
    
    def serialnumbers(self):
        return [x.serialnumber for x in self]
    
    def udids(self):
        return [x.udid for x in self]
    
    def names(self):
        return [x.name for x in self]

    def unsupervised(self):
        return DeviceList([x for x in self if not x.supervised])

    def supervised(self):
        return DeviceList([x for x in self if x.supervised])


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

        # paths to various resources
        self.resources = os.path.dirname(self.config.file)
        r = self._setup()
        self._devicepath = r['Devices']
        self.profiles = r['Profiles']
        self.images = r['Images']
        self.supervision = r['Supervision']
        self.logs = r['Logs']

        try:
            self.config.read()
        except config.Error as e:
            self.log.error(e)
            self.config.write({})
        
        self.task = TaskList(id, path=self.resources, logger=self.log)
        self.apps = AppManager(id, path=self.resources, logger=self.log)

        self._lookup = self.config.setdefault('Devices', {})
        self.idle = self.config.setdefault('Idle', 300)

        _reporting = self.config.get('Reporting', {'Slack': {}})
        self.log.debug("reporting: {0}".format(_reporting))
        self.report = reporting.reporterFromSettings(_reporting, 
                                                        self.log)

        self._cfgutillog = os.path.join(self.logs, 'cfgexec.log')        
        self._device = {}
        self._erased = []
        self._list = None
        self._auth = None

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
        # sync the TaskList
        # 
        self.stopped = True
        if reason:
            self.config.update({'StopReason': reason})
        _reason = reason if reason else 'no reason specified'
        self.log.debug("stopping for {0}".format(_reason))
        raise Stopped(_reason)

    def manage(self, device):
        '''Placeholder for future management check
        Returns True (for now)
        '''
        return True
            
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

    def findall(self, ecids=None, exclude=[]):
        '''returns list of Device objects for specified ECIDs
        '''
        if ecids is None:
            if not self._lookup:
                self.log.debug("lookup was reset... refreshing")
                self._lookup = self.config.get('Devices', {})
            ecids = self._lookup.keys()

        try:
            devices = DeviceList([self.device(x) for x in ecids 
                                                  if x not in exclude])
        except:
            self.log.error("failed to find devices")
            self.log.debug("recovering...")
            # an error can be thrown if findall() is called before
            # a device record has been created
            devices = DeviceList()
            for info in self.list():
                _ecid = info['ECID']
                if _ecid in ecids and _ecid not in exclude:
                    devices.append(self.device(_ecid, info))

        return devices

    def available(self, ecids=False):
        '''Returns list of all devices (or device ECID's) that are
        currently checked in
        '''
        devices = self.findall([i['ECID'] for i in self.list()])
        if ecids:
            return devices.ecids()
        return devices
    
    def device(self, ecid, info={}):
        '''Returns Device object from ECID
        '''
        try:    
            # return a cached device object (if we have one)
            return self._device[ecid]
        except KeyError:
            # self.log.debug("no cached device record")
            pass        

        # initialize device object from disk, and cache it
        devicerecords = self._devicepath
        try:
            # use the lookup table to translate the ECID -> UDID
            udid = self._lookup[ecid]
            _device = Device(udid, info, path=devicerecords)
            self._device[ecid] = _device
            _device = Device(udid, info, path=devicerecords)
            self._device[ecid] = _device
            return _device
        except KeyError:
            self.log.debug("no device record found")
        
        # no existing device 
        self.log.debug("creating new device record")
        udid = info['UDID']
        ecid = info['ECID']
        _device = Device(udid, info, path=devicerecords)
        lock = config.FileLock('/tmp/new-device', timeout=5)
        # update serialized lookup table and force a cache refresh
        with lock.acquire():
            _lookup = self.config.get('Devices', {})
            _lookup.update({ecid: udid})
            self.config.update({'Devices': _lookup})
            # force a refreshed lookup first time findall() is called
            self._lookup = {}
            self._device[ecid] = _device
        _device.restarting = False
        self.task.query('serialNumber', [ecid])
        self.task.erase([ecid])
        
        return _device
                               
    def find_new_apps(self, device):
        '''Use the Appmanager to find and report new, user-installed 
        applications
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
        ## list of apps that aren't known to the Appmanager
        userapps = self.apps.unknown(device, appnames)
        # only report if new apps were found
        if userapps:
            # TO-DO: design mechanism for tracking repeat installations
            smsg = "new user apps: {0}".format(userapps)
            msg = "NEW: {0}: {1}".format(device.name, smsg)
            self.log.info(msg)
            self.report.send(msg)
        else:
            self.log.debug("{0}: no new apps".format(device.name))
    
    def list(self, refresh=False):        
        '''Returns list of attached devices using cfgutil.list()
        '''
        # attempt to keep listing down to once per 30 seconds
        now = datetime.now()
        _stale = now - timedelta(seconds=30)
        _lastlisted = self.config.get('lastListed')
        if refresh or not self._list or (_stale > _lastlisted):
            self.log.info("refreshing device list")
            self._list = cfgutil.list(log=self.log)
            self.config.update({'lastListed':now})
        return self._list

    def need_to_erase(self, device):
        '''Reserved for future conditional erasing
        Returns True (for now)
        '''
        device.delete('erased')
        self.task.query('installedApps', [device.ecid])
        return True

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
                self.log.error("unexpected error occurred: {0!s}".format(e))
                raise e

        if _use_tethering:
            self.log.debug("using tethering")
            sns = devices.serialnumbers()
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
            cfgutil.install_wifi_profile(devices.ecids(), wifi, 
                                    log=self.log, file=self._cfgutillog)
            time.sleep(2)

    def checkin(self, info, run=True):
        '''process of device attaching
        '''
        device = self.device(info['ECID'], info)
        
        # mechanism to stall while devices restart
        if self.stopped:
            self.waitfor(device, 'restart')                

        # clearer logging
        if device.name.startswith('iPad'):
            # e.g. 'iPad (0x00000000001)'
            name = "{0} ({1})".format(device.name, device.ecid)
        else:
            name = device.name

        ## Pre-checkin

        # this needs to be re-worked
        reset = False
        if not device.checkin:
            # first time seeing the device
            self.log.debug("{0}: new device found!".format(name))
            if self.managed(device):
                reset = self.need_to_erase(device)
        else:
            try:
                # see if the device was checked since last checkin
                checkedout = device.checkout > device.checkin
            except TypeError:
                self.log.debug("{0}: never checked out".format(name))
                checkedout = False
            
            if checkedout:
                self.log.info("{0}: was checked out".format(name))
                reset = self.need_to_erase(device)
                self.verified = False
            else:
                self.log.info("{0}: was not checked out".format(name))

        # if device needs to be erased
        if reset:
            self.log.debug("{0}: will be reset".format(name))
            self.task.erase([device.ecid])
            self.task.query('installedApps', [device.ecid])
            device.checkin = datetime.now()
        else:
            self.log.debug("{0}: will not be reset".format(name))
            
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
            device.restarting = False
        else:
            self.log.info("{0}: checked out".format(device.name))            
            device.checkout = datetime.now()

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
                time.sleep(2)
                self.log.debug("waiting on {0}: {1}".format(reason, 
                                                            waiting))
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
        
        available = self.available().ecids()
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
        for device in self.findall(ecidset):
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
                    self.find_new_apps(device)
                
            else:
                err = "no results returned for device: {0}"
                self.log.error(err.format(device.name))

            ## old (broken) mechanism for tracking apps (see above)     
            # if _cache.has_key('installedApps'):
            #     if _cache['installedApps'].get(device.ecid):
            #         _installed = info.get('installedApps', [])
            #         device.apps = _installed 
            #         if _installed: 
            #             # record new apps (if any)
            #             self.find_new_apps(device, _installed)


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

    def erase(self, devices):
        '''Erase specified devices and mark them for preparation
        '''
        # get subset of device ECIDs that need to be erased
        ecids = self.task.erase(only=devices.ecids())

        if not ecids:
            self.log.info("no devices need to be erased")
            return

        ## EXTRA LOGGING: (doesn't really do anything)
        _missing = self.task.list('erase')
        if _missing:
            names = self.findall(_missing).names()
            self.log.error("missing devices tasked for erase")
            self.log.debug("missing: {0}".format(names))

        # mark restart before erase (or will count as checkout)
        for device in self.findall(ecids):
            self.log.debug("found device: {0}".format(device.name))
            device.restarting = True
    
        
        excluded = []
        erased = []
        failed = []
        try: 
            self.verified = False
            self.log.info("erasing devices: {0}".format(ecids))
            result = cfgutil.erase(ecids, log=self.log, 
                                   file=self._cfgutillog)
            erased = result.ecids
            failed = result.missing

        except cfgutil.FatalError as e:
            # no device was erased
            self.log.debug("erase: fatal error occurred")
            self.log.error(str(e))
            failed = ecids
            if "complete the activation process" in e.message:
                # handle devices that are activation locked
                _locked = self.findall(e.affected)
                err = "activiation locked: {0}".format(_locked.names())
                self.log.error(err)
                self.report.send(err)
                ## mechanism for isolating activation locked devices
                # self.lockdevices(e.affected)
                ## keep these ECIDs from being retasked
                excluded = e.affected
            raise

        except cfgutil.CfgutilError as e:
            # some devices were erased (continue with working devices)
            erased = e.unaffected
            failed = e.affected

        except Exception as e:
            # unknown error
            self.log.error("erase: unexpected error: {0!s}".format(e))
            failed = ecids
            raise e

        finally:
            if failed:
                _devices = self.findall(failed)
                names = _devices.names()
                self.log.error("erase failed: {0}".format(names))
                self.task.erase(failed, exclude=excluded)
                self.log.debug("re-tasked: {0}".format(failed))
                ## extra logging
                if excluded:
                    _msg = "excluding: {0}".format(excluded)
                    self.log.debug(_msg)
                # unmark failed devices as restarting
                for device in _devices:
                    device.restarting = False
            else:
                self.log.info("all devices were successfully erased!")

                
        ## process erased devices
        # task devices for supervision and app installation
        self.task.prepare(erased)
        self.task.installapps(erased)

        for device in self.findall(erased):
            device.erased = datetime.now()

        self.task.add('restart', erased)
        self.stop(reason='restart')
    
    def supervise(self, devices):
        '''All encompassing supervision
        devices are stripped down to unsupervised
        '''
        ## Check if manager has been stopped
        if self.stopped:
            raise Stopped("device supervision was stopped")

        # list of device ECID's that need supervision
        ecids = self.task.prepare(only=devices.unsupervised().ecids())                

        if not ecids:
            self.log.info("no devices need to be supervised")
            return

        ## EXTRA LOGGING: (doesn't really do anything)
        _missing = self.task.list('prepare')
        if _missing:
            names = self.findall(_missing).names()
            self.log.error("missing devices tasked for preparation")
            self.log.debug("missing: {0}".format(names))

        # make sure device network checks out
        try:
            self.check_network(self.findall(ecids), tethered=True)
        except tethering.Error as e:
            self.log.error("network error: {0!s}".format(e))
            self.check_network(self.findall(ecids), tethered=False)
    
        prepared, failed = [], []
        try:
            self.log.info("preparing devices: {0}".format(ecids))
            self.verified = False
            result = cfgutil.prepareDEP(ecids, log=self.log, 
                                        file=self._cfgutillog)
            prepared, failed = result.ecids, result.missing

        except cfgutil.CfgutilError as e:
            self.log.error("supervision partial failed: {0!s}".format(e))
            prepared, failed = e.unaffected, e.affected

        except cfgutil.FatalError as e:
            self.log.error("supervision failed: {0!s}".format(e))
            if "must be erased" in e.message:
                failed = e.ecids
                self.task.erase(failed)
            elif e.detail == "Network communication error.":
                # started happening a lot with macOS10.12 and iOS12.1
                # restarting the device seems to fix the issue, but
                # there's no way to restart an unsupervised device
                # without physical interaction
                # tethering.stop(self.log) # doesn't fix
                # SOLUTION: installing Wi-Fi profile works
                # TO-DO: Retry mechanism
                
                # too nested for my liking
                try:
                    self.log.debug("attempting to recover")
                    self.check_network(self.findall(ecids), 
                                              tethered=False)
                    result = cfgutil.prepareDEP(ecids, log=self.log, 
                                        file=self._cfgutillog)
                    prepared, failed = result.ecids, result.missing
                except cfgutil.FatalError as e:
                    err = "recovery partially failed: {0!s}".format(e)
                    self.log.err(err)
                    failed = e.ecids
                except cfgutil.CfgutilError as e:                    
                    err = "recovery partially failed: {0!s}".format(e)
                    self.log.err(err)
                    prepared = e.unaffected
                    failed = e.affected
            else:
                # put everything back into the queue
                failed = e.ecids

            if not prepared:
                raise

        except Exception as e:
            self.log.error("prepare: unexpected error: {0!s}".format(e))
            failed = e.ecids
            raise e

        finally:
            # re-task any failed devices
            self.task.prepare(failed)
            self.task.query('isSupervised', prepared)
            prepared_devices = self.findall(prepared)
            names = prepared_devices.names()
            self.log.info("successfully prepared: {0}".format(names))
            for device in prepared_devices:
                device.enrolled = datetime.now()
                device.supervised = True
            self.set_background(prepared_devices, 'alert')

    def installapps(self, devices):
        if self.stopped:
            raise Stopped("skipped app installation")

        # get the ECIDs of the devices tasked for app installation
        ecids = self.task.installapps(only=devices.ecids())
        if not ecids:
            self.log.info("no apps need to be installed")
            return

        ## EXTRA LOGGING: (doesn't really do anything)
        _missing = self.task.list('installapps')
        if _missing:
            names = self.findall(_missing).names()
            self.log.error("missing devices for app installation")
            self.log.debug("missing: {0}".format(names))


        devices = self.findall(ecids)
        self.log.info("installing apps: {0}".format(devices.names()))
        for _devices, apps in self.apps.breakdown(devices):
            # would like to switch ACAdapter to use ecids (eventually)
            udids = _devices.udids()
            try:
                self.log.info("{0} installing {1}".format(udids,apps))
                self.verified = False
                adapter.install_vpp_apps(udids,apps,skip=True,wait=True)
            except adapter.ACAdapterError as e:
                self.log.error(e)
                self.task.installapps(_devices.ecids())
                raise
            except Exception as e:
                err = "installapps: unexpected error: {0!s}".format(e)
                self.log.error(err)
                raise e
        self.task.query('installedApps', devices.ecids())
        
    def set_background(self, devices, _type):
        '''set the background of the specified devices
        '''
        if self.stopped:
            raise Stopped("skipping wallpaper")

        if not devices:
            self.log.error("background: no devices specfied")
            return

        if not self.images:
            self.log.error("no images availalbe")
            return

        # background cannot be set on unsupervised devices
        ecids = devices.supervised().ecids()
        if not ecids:
            self.log.info("no wallpaper modified")
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
            for device in self.findall(result.ecids):
                device.background = _type
        except cfgutil.CfgutilError as e:
            self.log.error("failed to set background: {0}".format(e))
            self.log.debug("unaffected: {0}".format(e.unaffected))
            self.log.debug("affected: {0}".format(e.affected))
        except KeyError as e:
            self.log.error("no image for: {0}".format(e))
            return

    def managed(self, device):
        return True

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
        available = []
        for info in self.list():
            device = self.device(info['ECID'], info)
            available.append(device.ecid)
            self.log.info("verifying: {0}".format(device.name))

            ## Verify device Serial Number
            if not device.serialnumber:
                self.log.error('  serial number: missing...')
                self.task.query('serialNumber', [device.ecid])
            else:
                self.log.info('   serial number: good!')

            ## Verify device Checkin
            if not device.checkin:
                self.log.error("        checkin: failed...")
                self.log.debug(" ... skipping additional verification")
                _verified = False
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
        unavailable = self.findall(exclude=available)

        remove_pending = []
        for device in self.findall(exclude=available):
            # skip restarting devices
            if device.restarting:
                continue

            # sanitize unavailable device records
            remove_pending.append(device.ecid)
            if not device.checkout:
                self.log.error("device was never checked out")
                device.checkout = datetime.now()
                self.task.remove(all=True)
        
        ## remove all pending tasks and queries for missing devices
        self.log.debug("removing unavailable tasks")
        self.task.remove(remove_pending, all=True)

        ## Re-task anything that failed verification
        for name,ecids in _tasks.items():
            # if any tasks have to be added then verification failed
            _verified = False
            self.task.add(name, ecids)
            msg = "_verify: retasked: {0}: {1}"
            self.log.debug(msg.format(name, ecids))
        
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
            self.log.debug("available: {0}".format(devices.names()))
    

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
            
            self.finalize()
            self.log.info("run finished")

if __name__ == '__main__':
    pass
