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
__version__ = '2.4.0'
__url__ = None
__all__ = [
    'DeviceManager', 
    'Stopped',
    'DeviceList'
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

class Error(Exception):
    pass


class Stopped(Error):
    '''Exception to interrupt and signal to other DeviceManagers
    '''
    def __init__(self, message, reason=None):
        super(self.__class__, self).__init__(message)
        self.reason = reason

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
            logger.addHandler(logging.NullHandler())
        self.log = logger

        self.lock = config.FileLock('/tmp/ipadmanager', timeout=5)
        self.config = config.Manager("{0}.manager".format(id), **kwargs)

        # paths to various resources
        self.resources = os.path.dirname(self.config.file)
        self._devicepath = os.path.join(self.resources, 'devices')
        self._cfgutillog = os.path.join(self.resources, 'log/cfgexec.log')
        self.profiles = os.path.join(self.resources, 'profiles')
        _imagedir = os.path.join(self.resources, 'images')
        _authdir = os.path.join(self.resources, 'supervision')

        try:
            self.config.read()
        except config.Error as e:
            self.log.error(e)
            self.config.write({})
        
        try:
            os.mkdir(self._devicepath)
        except OSError as e:
            # re-raise errors if not EEXIST or 
            if e.errno != 17 and not os.path.isdir(self._devicepath):
                self.log.error(e)
                raise

        self.task = TaskList(id, path=self.resources, logger=self.log)
        self.apps = AppManager(id, path=self.resources, logger=self.log)

        _reporting = self.config.get('reporting', {'Slack': {}})
        self.report = reporting.reporterFromSettings(_reporting)


        self._lookup = self.config.setdefault('devices', {})
        self.idle = self.config.setdefault('idle', 300)
        # _quarantine = self.config.setdefault('quarantine', [])
        # self._quarantined = set(_quarantine)
        
        self._images = self.config.get('images', _imagedir)
        self._supervision = self.config.get('supervision', _authdir)

        self._device = {}
        self._erased = []
        self._list = None
        self._auth = None
        self._checkin = []

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
        raise Stopped("Hold the press!")
            
    def findall(self, ecids=None, exclude=[]):
        '''returns list of Device objects for specified ECIDs
        '''
        if ecids is None:
            if not self._lookup:
                self.log.debug("lookup was reset... refreshing")
                self._lookup = self.config.get('devices', {})
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
                               
    def find_new_apps(self, device, applist):
        '''Use the Appmanager to find and report new, user-installed 
        apps using slack
        '''
        # `cfgutil get installedApps` provides a list of dicts
        #   using 4 keys: ['itunesName', 'displayName',
        #                  'bundleIdentifier', 'bundleVersion']
        # apps are installed using 'itunesName', and 'displayName' 
        # is useful only when parsing GUI
        appnames = []
        for app in applist:
            name = app.get('itunesName')
            if name:
                appnames.append(name)
        # get list of apps that aren't known to the Appmanager
        _new = self.apps.unknown(device, appnames)
        # only report if new apps were found
        if _new:
            userapps = [str(x) for x in _new]
            smsg = "new user apps: {0}".format(userapps)
            msg = "NEW: {0}: {1}".format(device.name, smsg)
            self.log.info(msg)
            self.report.send(msg)
    
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
            self.config.update({'lastListed': now})
        return self._list

    def need_to_erase(self, device):
        '''Reserved for future conditional erasing
        Returns True (for now)
        '''
        device.delete('erased')
        self.task.query('installedApps', [device.ecid])
        return True

    def check_network(self, devices):    
        _use_tethering = False
        if _use_tethering and not tethering.enabled(log=self.log):
            self.log.info("Device Tethering isn't enabled...")
            try:
                tethering.restart(timeout=30)
            except tethering.Error as e:
                self.log.error(e)
                _use_tethering = False
            except Exception as e:
                self.log.error("unexpected error occurred: {0!s}".format(e))
                raise

        if _use_tethering:
            self.log.debug("using tethering")
            sns = devices.serialnumbers()
            tethered = tethering.devices_are_tethered(sns)
            timeout = datetime.now() + timedelta(seconds=60)
            while not tethered:
                time.sleep(5)
                tethered = tethering.devices_are_tethered(sns)
                if datetime.now() > timeout:
                    self.log.error("timed out waiting for devices")
                    break
                
            if not tethered:
                try:
                    # this will have to be removed eventually
                    tethering.restart(timeout=20)
                    return
                except tethering.Error as e:
                    self.log.error(e)
                    raise
        else:
            # too hidden for my liking, but whatever
            self.log.debug("using wifi profile")
            wifi = os.path.join(self.profiles, 'tmpWifi.mobileconfig')
            cfgutil.install_wifi_profile(devices.ecids(), wifi, 
                                    log=self.log, file=self._cfgutillog)
            time.sleep(2)

    def checkin(self, info, verifying=False):
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

        # this needs to be re-worked
        erase = False
        if not device.checkin:
            # first time seeing the device
            self.log.debug("{0}: never checked in".format(name))
            erase = self.need_to_erase(device)
        else:
            try:
                # see if the device was checked since last checkin
                checkedout = device.checkout > device.checkin
            except TypeError:
                self.log.debug("{0}: never checked out".format(name))
                checkedout = False
            
            if checkedout:
                self.log.info("{0}: was checked out".format(name))
                erase = self.need_to_erase(device)
            else:
                self.log.info("{0}: was not checked out".format(name))

        # if device needs to be erased
        if erase:
            self.log.info("{0}: will be erased".format(name))
            self.task.erase([device.ecid])
        else:
            self.log.debug("{0}: will not be erased".format(name))
            
        device.checkin = datetime.now()
        
        # TO-DO: re-work
        # verify will call run() if it needs to
        if not verifying:
            self.run(device.ecid)

    def checkout(self, info):
        '''saves timestamp of device checkout (if not restarting)
        '''
        device = self.device(info['ECID'], info)

        # skip checkout if device has been marked for restart
        if device.restarting:
            self.log.info("{0}: restarting...".format(device.name))
            device.restarting = False
        else:
            self.log.info("{0}: checked out".format(device.name))            
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

    def run_queries(self):
        self.log.debug("checking for queries")
        if not self.task.queries():
            self.log.info("no queries to perform")
            return
            
        _cache, ecidset = {}, set()
        # merge all of the queries into one 
        for q in self.task.queries():
            # empty the query of all ECIDs (preserved in _cache)
            _cache[q] = self.task.query(q)
            # create a set of all unique ECIDs
            ecidset.update(_cache[q])

        # list of all keys for cfgutil.get()
        queries = _cache.keys()
        self.log.debug("queries: {0}: {1}".format(queries, ecidset))
        try:
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

        ## process the results (per device)
        # if device is missing from the result
        for device in self.findall(ecidset):
            # parse the result this device
            info = result.get(device.ecid, {})
            _installed = info.get('installedApps', [])
            device.apps = _installed 
            if _installed: 
                # record new apps (if any)
                self.find_new_apps(device, _installed)

            # iterate the cache to find queries for this device
            for q,ecids in _cache.items():
                if device.ecid in ecids:
                    # get the value of the query result
                    v = info.get(q)
                    if v is not None:
                        device.update(q, v)
                    # remove successful queries from the cache
                    ecids.remove(device.ecid)

        # cache should only be made up of failed queries at this point
        # TO-DO: test cache removes successful queries
        for q,ecids in _cache.items():
            if ecids:
                msg = 're-building query: {0}: {1}'.format(q,ecids)
                self.log.debug(msg)
                self.task.query(q, ecids)

        # forward along the results for processing elsewhere
        return result

    def erase(self, devices):
        '''Erase specified devices and mark them for preparation
        '''
        
        ecids = self.task.erase(only=devices.ecids())

        if not ecids:
            self.log.info("no devices need to be erased")
            return devices

        # more logging (doesn't really do anything)
        _missing = self.task.list('erase')
        if _missing:
            names = self.findall(_missing).names()
            self.log.error("missing devices tasked for erase")
            self.log.debug("missing: {0}".format(names))

        # update devices before erase
        for device in self.findall(ecids):
            # mark restarting before erase (or will count as checkout)
            self.log.debug("found device: {0}".format(device.name))
            device.restarting = True
    
        try: 
            self.log.info("erasing devices: {0}".format(ecids))
            result = cfgutil.erase(ecids, log=self.log, 
                                   file=self._cfgutillog)
        except cfgutil.CfgutilError as e:
            self.log.error("erase failed: {0}".format(e))
            if "complete the activation process" in e.message:
                err = "unable to erase activation locked device"
                self.log.error(err)
                self.report.send(err)
                # self.lockdevices(e.affected)
                self.task.erase(e.unaffected)
            else:
                self.task.erase(e.affected)
            return
        except Exception as e:
            self.log.error("erase: unexpected error: {0!s}".format(e))
            self.log.info("re-tasking erase: {0}".format(ecids))
            self.task.erase(ecids)
            return

        erased, failed = result.ecids, result.missing

        # process devices that failed to erase (if any)
        if failed:
            self.log.error("erase failed: {0}".format(failed))
            self.task.erase(failed)
            for device in self.findall(failed):
                device.restarting = False
        else:
            self.log.info("all devices were successfully erased!")
                
        ## process erased devices
        # task devices for supervision and app installation
        self.task.prepare(erased)
        self.task.installapps(erased)
        for device in self.findall(erased):
            # update timestamp (resets various record keys)
            device.erased = datetime.now()

        # task device for preparation
        self.task.add('restart', erased)
        self.log.debug("device: {0}".format(device.record))
        self.stop(reason='restart')
    
    def supervise(self, devices):
        # this is messy because it accepts devices and returns devices
        # but also sometimes ignores devices... whatever
        if self.stopped:
            raise Stopped("skipped device supervision")

        # list of device ECID's that need supervision
        ecids = self.task.prepare(only=devices.unsupervised().ecids())                

        if not ecids:
            self.log.info("no devices need to be supervised")
            return

        # more logging (doesn't really do anything)
        _missing = self.task.list('prepare')
        if _missing:
            names = self.findall(_missing).names()
            self.log.error("missing devices tasked for preparation")
            self.log.debug("missing: {0}".format(names))

        # make sure device network checks out
        self.check_network(self.findall(ecids))
    
        prepared, failed = [], []
        try:
            self.log.info("preparing devices: {0}".format(ecids))
            result = cfgutil.prepareDEP(ecids, log=self.log, 
                                        file=self._cfgutillog)
            prepared, failed = result.ecids, result.missing
        except cfgutil.CfgutilError as e:
            self.log.error("possible failure: {0!s}".format(e))
            prepared, failed = e.unaffected, e.affected
        except cfgutil.FatalError as e:
            self.log.error("prepare failed: {0!s}".format(e))
            # self.recover(e)
            if "must be erased" in e.message:
                failed = e.ecids
            elif e.detail == "Network communication error.":
                # started happening a lot with macOS10.12 and iOS12.1
                # restarting the device seems to fix the issue, but
                # there's no way to restart an unsupervised device
                # without physical interaction
                # tethering.stop(self.log) # doesn't fix
                # IDEA: could (maybe) install Wi-Fi profile and retry
                prepared, failed = e.unaffected, e.affected
            else:
                # put everything back into the queue
                failed = e.ecids
            raise
        except Exception as e:
            self.log.error("prepare: unexpected error: {0!s}".format(e))
            failed = e.ecids
            raise
        finally:
            # re-task any failed devices
            self.task.prepare(failed)
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

        # more logging (doesn't really do anything)
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
                adapter.install_vpp_apps(udids,apps,skip=True,wait=True)
            except adapter.ACAdapterError as e:
                self.log.error(e)
                self.task.installapps(_devices.ecids())
                raise
            except Exception as e:
                err = "installapps: unexpected error: {0!s}".format(e)
                self.log.error(err)
                raise
        
    def authorization(self):
        '''Uses the directory specified to work out the private key
        and certificate files used for cfgutil
        returns ACAuthentication object
        '''
        if not self._auth:
            self.log.debug("getting authorization for cfgutil")
            dir = self._supervision
        
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

    def set_background(self, devices, _type):
        '''needs to be re-adapted to new layout
        '''
        # IDEA: another class for listing types of devices
        #   self.devices.connected
        #   self.devices.available
        #   self.devices.supervised
        if not devices:
            self.log.error("background: no devices specfied")
            return

        if not self._images:
            self.log.error("no images availalbe")
            return

        ecids = devices.supervised().ecids()
        if not ecids:
            if devices:
                self.log.error("can't ajust background on"
                               " non-supervised devices")
            self.log.info("no backgrounds modified")
            return

        images = {}
        for file in os.listdir(self._images):
            name, ext = os.path.splitext(file)
            if ext in ['.png','.jpeg','.jpg']:            
                path = os.path.join(self._images, file)
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

    @property
    def verified(self):
        '''Placeholder for future verification 

        returns False (for now)
        
        because they system should be self healing, re-runs
        shouldn't do anything if everything is worked
        '''
        self.log.debug("verified: verifying devices")
        # this should be made into a method
        try:
            config.FileLock('/tmp/ipad-restart.lock').acquire(timeout=0)
        except config.TimeoutError:
            self.log.debug("restarting... skipping verification")
            return True
            
        devicelist = self.list()
        
        _tasks = {}
        _verified = True
        for info in devicelist:
            device = self.device(info['ECID'], info)
            name = device.name
            msg = "verify: {0}".format(name)

            self.log.debug("{0}: checking serialnumber".format(msg))
            if not device.serialnumber:
                self.log.error("{0}: serialnumber missing".format(msg))
                self.task.query('serialNumber', [device.ecid])
                _verified = False
            
            ## Checkin check
            self.log.debug("{0}: checking checkin".format(msg))
            if not device.checkin:
                self.log.error("{0}: never checked in".format(msg))
                self._checkin.append(info)
                _verified = False
                self.log.debug("{0}: skipping other checks".format(msg))
                continue

            ## Erase check
            self.log.debug("{0}: checking erase".format(msg))
            if not device.erased:
                self.log.error("{0}: never erased".format(msg))
                erase = _tasks.setdefault('erase', [])
                erase.append(device.ecid)
                self.log.debug("{0}: skipping other checks".format(msg))
                continue
                
            ## Enrollment check
                # we're just going to have task it for enrollment 
                # and trust it will work for now
                
                ## prepared devices are not necessarily supervised
                # self.task.query('isSupervised', [ecid])

                # I would also like to add some code to look for previous
                # errors (maybe it couldn't enroll for a reason)

                # this will have to be designed and tested
                # idea is to load a callback function into the query to 
                # check the result once the query is made

                # create query and callback for processing
                # self.task.query('isSupervised', [ecid], 
                #                 self._isSupervised)
            self.log.debug("{0}: checking enrollment".format(msg))
            if not device.enrolled:
                self.log.error("{0}: never enrolled".format(msg))
                enroll = _tasks.setdefault('prepare', [])
                enroll.append(device.ecid)
            # might be a messy bandaid...
            elif (device.checkin < device.erased < device.enrolled):
                # remove this ECID from the prepare
                ecid = self.task.get('prepare', only=[device.ecid])
                _msg = "{0}: removed prepare task".format(msg)
                if ecid:                    
                    self.log.debug(_msg)
             
            ## App check
            self.log.debug("{0}: checking apps".format(msg))
            if not device.apps:
                # device missing all apps
                self.log.error("{0}: no apps installed".format(msg))
                installapps = _tasks.setdefault('installapps', [])
                installapps.append(device.ecid)
            else:
                # set of all apps that should be installed
                appset = set(self.apps.list(device))
                # results in empty set() if all apps are installed
                appnames = [x['itunesName'] for x in device.apps]
                _missing = list(appset.difference(appnames))
                if _missing:
                    # some apps are not installed
                    err = "{0}: missing apps: {1}".format(msg, _missing)
                    self.log.error(err)
                    installapps = _tasks.setdefault('installapps', [])
                    installapps.append(device.ecid)
        
        # update all tasks in an accumulative swoop
        for name,ecids in _tasks.items():
            # if any tasks have to be added then verification failed
            _verified = False
            self.task.add(name, ecids)
        
        if not _verified:
            self.log.error("verification failed")
            self.log.debug("retasked: {0}".format(_tasks))
            

        return _verified
        
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
            for info in self._checkin:
                # checkin the device without calling run()
                self.checkin(info, verifying=True)
            self.run()

    def finalize(self):
        '''Redundant finalization checks, verify tasks completed, 
        and adjust backgrounds of supervised devices
        '''
        if self.stopped:
            self.log.debug("finalization skipped")
            self.config.update({'finished':datetime.now()})
            return
        else:
            self.log.debug("finalizing devices")

        self.log.debug("finalization: adding queries")
        devices = self.available()
        self.task.query('isSupervised', devices.ecids())
        self.task.query('installedApps', devices.ecids())
        # consume queries before labeling retasked ECIDs
        self.run_queries()

        retasked_ecids = set()
        if not self.verified:
            self.log.error("finalization: verification failed")
            self.log.info("Adding to agenda:")
            for k,v in self.task.record.items():
                if v:
                    retasked_ecids.update(v)
                    self.log.info("{0}: {1}".format(k,v))
        
        ## Find devices that need wallpaper changed (supervised only)
        finished, unfinished = DeviceList(), DeviceList()
        for device in devices:
            if device.ecid in retasked_ecids:
                if device.background != 'alert':
                    unfinished.append(device)
            elif device.background != 'background':
                finished.append(device)

        try:
            if unfinished:
                self.set_background(unfinished, 'alert')
            if finished:
                self.set_background(finished, 'background')
        except cfgutil.Error as e:
            self.log.error("unable to set backgrounds")
            
        self.config.update({'finished':datetime.now()})
        self.log.debug("finalization completed")
            
    def run(self, ecid=None):
        # keep multiple managers from running simultaneously
        # will be changed in future version
        with self.lock.acquire(timeout=-1):
            # if ecid is tasked for restart, skip this run
            if ecid and ecid in self.task.list('restart'):
                msg = "{0}: restarting: skipping run".format(ecid)
                self.log.debug(msg)
                return
            
            if self.task.alldone():
                # exit early if no tasks exist
                self.log.info("all tasks have been completed")
                self.finalize()
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
            except Exception as e:
                self.log.error("unexpected error: {0!s}".format(e))

            ## Prepare devices (least critical step w/ DEP)
            try:
                self.supervise(devices)
            except Stopped as e:
                self.log.info(e)
                return
            except Exception as e:
                self.log.error("unexpected error: {0!s}".format(e))
                self.log.error(e)

            try:
                self.installapps(devices)
            except Stopped as e:
                self.log.info(e)
                return
            except Exception as e:
                self.log.error(e)
            
            self.finalize()

if __name__ == '__main__':
    pass
