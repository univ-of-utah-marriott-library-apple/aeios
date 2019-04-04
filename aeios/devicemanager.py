# -*- coding: utf-8 -*-

import os
import time
import logging

import datetime as dt

import apps
import config
import reporting
import tethering

from tasklist import TaskList
from device import Device, DeviceList, DeviceError
from actools import cfgutil

"""
Manage and Automate iOS devices
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "2.7.0"
__all__ = ['DeviceManager', 'Stopped']

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())


class Error(Exception):
    pass


class Stopped(Error):
    """
    Exception to interrupt and signal to other DeviceManagers
    """
    def __str__(self):
        return "STOPPED: " + str(self.message)


class CacheError(Error):
    pass


class Cache(object):

    def __init__(self, conf):
        self.log = logging.getLogger(__name__ + '.Cache')
        self.devices = DeviceList()
        self.conf = conf
                
    @property
    def listed(self):
        return self.conf.get('Devices', [])

    @listed.setter
    def listed(self, value):
        self.conf.update({'Devices': value})
    
    def device(self, ecid):
        for d in self.devices:
            if ecid == d.ecid:
                return d
        raise CacheError("{0!s}: not in cache".format(ecid))
        
    def add(self, device):
        if device not in self.devices:
            self.log.debug("cached device: %s", device)
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
    """
    Manage and automate iOS Devices
    """
    def __init__(self, _id='edu.utah.mlib.ipad', logger=None, **kwargs):
        self.log = logger if logger else logging.getLogger(__name__)

        self.lock = config.FileLock('/tmp/ipadmanager', timeout=5)
        self.config = config.Manager("{0}.manager".format(_id), **kwargs)
        self.file = self.config.file

        # paths to various resources
        resources = os.path.dirname(self.config.file)
        r = ['Devices', 'Supervision', 'Images', 
             'Profiles', 'Logs', 'Apps']
        self.resources = Resources(resources, r)
        self.images = self.resources.images
        self.profiles = self.resources.profiles
        
        try:
            self.config.read()
        except config.Error as e:
            self.log.error("unable to read config: %s", e)
            self.log.debug("creating default config")
            self.config.write({'Reporting': {'Slack': {}},
                               'Devices': [],
                               'Idle': 300})
        self.cache = Cache(self.config)
        self.task = TaskList(_id, path=str(self.resources))
        self.apps = apps.AppManager(_id, self.resources)

        _reporting = self.config.get('Reporting', {'Slack': {}})
        self.log.debug("reporting: %r", _reporting)
        self.reporter = reporting.reporterFromSettings(_reporting) 

        self.idle = self.config.setdefault('Idle', 300)

        cfgutil.log = os.path.join(self.resources.logs, 'cfgexec.log')  

        self.auth = None
        self._install_local_apps = False

    @property
    def running(self):
        """
        :return: True if currently running
        """
        try:
            with self.lock.acquire(timeout=0.05):
                return False
        except config.TimeoutError:
            return True

    @property
    def stopped(self):
        return self.config.get('Stopped', False)
    
    @stopped.setter
    def stopped(self, value):
        self.config.update({'Stopped': value})

    def stop(self, reason=None):
        """
        Stop automation
        """
        self.stopped = True
        if reason:
            self.config.update({'StopReason': reason})
        _reason = reason if reason else 'no reason specified'
        self.log.debug("stopping for %s", _reason)
        raise Stopped(_reason)

    def managed(self, device):
        """
        Placeholder for future management check

        :param Device device:

        :returns: True if device is managed, otherwise False
        """
        try:
            _managed = device.managed
            self.log.debug("%s: managed: %s", device, device.managed)
            return _managed
        except AttributeError:
            self.log.debug("%s: has no managed attribute", device)
            return True

    def manage(self, device):
        """
        Placeholder for adding device to automated tasks
        Does nothing for now
        """
        self.log.debug("%s: managing device", device)
        device.managed = True

    def authorization(self):
        """
        Uses the directory specified to work out the private key
        and certificate files used for cfgutil
        returns ACAuthentication object
        """
        if not self.auth:
            self.log.debug("getting authorization for cfgutil")
            directory = self.resources.supervision
        
            if not os.path.isdir(directory):
                err = "no such directory: {0!r}".format(directory)
                raise Error(err)
            key, cert = None, None
            for item in os.listdir(directory):
                path = os.path.join(directory, item)
                if item.endswith('.crt'):
                    cert = path
                elif item.endswith('.key') or item.endswith('.der'):
                    key = path
            if key and cert:
                self.auth = cfgutil.Authentication(key, cert)
        return self.auth

    def records(self, ecids=None):
        """
        :returns: list of tuples for specified device records
            if no ECIDs are specified, returns all device records
            e.g. [(ECID1, path), (ECID2, path), ...]
        """
        # list all files in directory (excluding hidden files)
        files = [x for x in os.listdir(self.resources.devices) 
                 if not x.startswith('.')]
        _records = []
        ecids = ecids or []
        for f in files:
            if f.endswith('.plist'):
                # remove '.plist' extension
                _ecid = os.path.splitext(f)[0]
                # return only specified ECIDs or everything
                if not ecids or _ecid in ecids:
                    # append tuple (ECID, path)
                    _records.append((_ecid, f))
        return _records

    def findall(self, ecids=None, exclude=()):
        """
        :returns: DeviceList of specified ECIDs

        if no ECIDs are specified, return DeviceList for all known devices
        """
        devices = DeviceList()
        for ecid, path in self.records(ecids):
            if ecid not in exclude:
                if not ecids or ecid in ecids:
                    devices.append(self.device(ecid))
        return devices            
    
    def available(self):
        """
        :returns: DeviceList of currently connected devices
        """
        devices = [self.device(x['ECID'], x) for x in self.list()]
        return DeviceList(devices)

    def unavailable(self):
        """
        :returns: DeviceList of non-connected devices
        """
        return self.findall(exclude=self.available().ecids)

    def device(self, ecid, info=None):
        """
        :returns: Device object        
        """
        try:
            # return cached device object (if we have one)
            _device = self.cache.device(ecid)
            if info:
                _device.updateall(info)
            return _device
        except CacheError:
            pass

        self.log.debug("creating new device object: %s", ecid)

        # check if we have an existing device record
        # if ecid not in [e for e,p in self.records()]:
        if ecid not in [x[0] for x in self.records()]:
            self.log.info("creating new device record: %s", ecid)
            self.task.query('serialNumber', [ecid])

        device = Device(ecid, info, path=self.resources.devices)

        self.cache.add(device)
        return device
                           
    def devices(self, ecids):
        return DeviceList([self.device(x) for x in ecids])

    def list(self, refresh=False, timeout=30):        
        """
        :returns: list of connected devices using cfgutil.list() 

        NOTE: cached and refreshed once every 30 seconds
        """
        # keep listing down to once per 30 seconds (and first run)
        now = dt.datetime.now()
        # set refresh to <timeout> seconds ago
        expires = now -  dt.timedelta(seconds=timeout)
        # default listed == refresh (triggering update)
        listed = self.config.setdefault('lastListed', expires)
        if refresh or listed <= expires:
            # update the cache and record the timestamp
            self.log.debug("refreshing device list")
            self.cache.listed = cfgutil.list()
            self.config.update({'lastListed': now})
        return self.cache.listed

    def need_to_erase(self, device):
        """
        :returns: True if device needs to be erased
        """
        self.log.info("%s: checking erase", device)

        # device is not managed (don't erase)
        if not self.managed(device):
            self.log.debug("%s: not managed", device)
            return False

        # device is restarting (don't erase)
        if device.restarting:
            self.log.debug("%s: restarting", device)
            return False
        
        # device has NEVER checked in (erase)
        if not device.checkin:
            self.log.debug("%s: new device found!", device)
            return True

        # device has not been erased (erase)
        if not device.erased:
            self.log.debug("%s: never erased", device)
            return True

        now = dt.datetime.now()

        # device has been erased in the last 10 minutes (don't erase)
        was_erased = now - device.erased
        if was_erased <  dt.timedelta(minutes=10):
            self.log.info("%s: recently erased", device)
            self.verified = False
            return False
        else:
            self.log.debug("%s: erase timeout expired", device)
        
        # This is where things get messy
        try:
            # if the device has been checked out since last checkin
            if device.checkout > device.checkin:
                # see if checkout happened less than 5 minutes ago
                self.log.debug("%s: was checked out", device)
                time_away = now - device.checkout
                self.log.debug("%s: checked out for: %s", device, time_away)
                if time_away >  dt.timedelta(minutes=5):
                    self.log.debug("%s: valid checkout", device)
                    return True
                else:
                    # reset checkout to 1 minute before last checkin
                    self.log.debug("%s: invalid checkout", device)
                    recover = device.checkin -  dt.timedelta(minutes=1)
                    self.log.debug("adjusted checkout: %s", recover)
                    device.checkout = recover
                    self.log.debug("invalidating verification")
                    self.verified = False
            else:
                self.log.debug("%s: not checked out", device)
        except TypeError:
            self.log.debug("%s: never checked out", device)
            # create dummy checkout 1 minute before checkin
            device.checkout = device.checkin -  dt.timedelta(minutes=1)
        
        return False        

    def check_network(self, devices, tethered=True):    
        # TO-DO: this needs to be tested to see that if tethering fails
        #        a wi-fi profile is used instead
        _use_tethering = tethered
        enabled = tethering.enabled()
        if _use_tethering and not enabled:
            self.log.info("Tethering isn't enabled...")
            try:
                tethering.restart(timeout=30)
            except tethering.Error:
                self.log.error("couldn't restart tethering")
                _use_tethering = False
            except Exception:
                self.log.exception("unexpected error occurred")
                raise

        if _use_tethering and enabled:
            self.log.debug("using tethering")
            sns = devices.serialnumbers
            tethered = tethering.devices_are_tethered(sns)
            timeout = dt.datetime.now() +  dt.timedelta(seconds=10)

            while not tethered:
                time.sleep(5)
                tethered = tethering.devices_are_tethered(sns)
                if dt.datetime.now() > timeout:
                    self.log.error("timed out waiting for devices")
                    break
                
            if not tethered:
                tethering.restart(timeout=10)
        else:
            # too hidden for my liking, but whatever
            self.log.debug("using wifi profile")
            wifi = os.path.join(self.profiles, 'wifi.mobileconfig')
            cfgutil.install_wifi_profile(devices.ecids, wifi)
            time.sleep(2)
        
        return enabled

    def checkin(self, info, run=True):
        """
        Process attached device
        """
        # update cache (add to cached list)
        self.cache.listed = self.cache.listed + [info]

        device = self.device(info['ECID'], info)
        device.verified = False

        # Pre-checkin

        # TO-DO:
        # validate checkin (currently done by need_to_erase())
        # - invalid:
        #       unmanaged, restarting, 
                
        if not self.managed(device):
            # TO-DO: add mechanism to prompt for device management
            self.log.info("ignoring unmanaged device: %s", device)
            return
        else:
            self.log.debug("%s: managed", device)
        
        if self.stopped:
            # mechanism to stall while devices restart            
            self.waitfor(device, 'restart')
            if device.restarting:
                device.restarting = False

        # Determine actions need to be taken
        if self.need_to_erase(device):
            self.log.debug("%s: will be erased", device)
            self.task.erase([device.ecid])
            self.task.query('installedApps', [device.ecid])
        else:
            self.log.debug("%s: will not be erased", device)
        
        # at this point all checks have been made and 
        device.checkin = dt.datetime.now()
        
        if run:
            self.run()

    def checkout(self, info):
        """
        Process detached device
        """
        # TO-DO: update cache (remove from cached list)
        #       - will require better way of managing the list
        #       - w

        device = self.device(info['ECID'], info)
        _cache = [d for d in self.cache.listed if d['ECID'] != device.ecid]
        self.cache.listed = _cache
        # IDEA: could just return if self.stopped (would eliminate need 
        #       for device restart tracking)

        # skip checkout if device has been marked for restart
        if not device.restarting:
            device.checkout = dt.datetime.now()
            self.log.info("%s: checked out", device)            
        else:
            self.log.debug("%s: restarting...", device)

        device.verified = False

    def waitfor(self, device, reason, wait=120):
        """
        Mechanism to stall run() during device restart
        """
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

        # this should block all devices until the stopped reason
        # has passed
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

            stoptime = dt.datetime.now() +  dt.timedelta(seconds=wait)
            while waiting:
                time.sleep(5)
                msg = "waiting on {0}: {1}".format(reason, waiting)
                self.log.debug(msg)
                waiting = self.task.list(reason)
                if dt.datetime.now() > stoptime:
                    self.log.debug("gave up waiting")
                    break                            
            self.stopped = False
            self.config.delete(_reason)

    def run_queries(self):
        """
        Run tasked queries using actools.cfgutil
        """
        self.log.info("running device queries...")
        if not self.task.queries():
            self.log.info("no queries to perform")
            return
        
        available = self.available().ecids
        # Temporary cache of existing queries
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
        self.log.debug("queries: %r: %r", queries, ecidset)
        try:
            self.verified = False
            result = cfgutil.get(queries, ecidset)
            self.log.debug("result: %r", result.output)
        except Exception:
            self.log.exception("unable to query devices")
            for q, ecids in _cache.items():
                self.log.debug('re-building queries: %r: %r', q, ecids)
                self.task.query(q, ecids)
            raise
        
        # Process results

        # all devices that were specified in the combined query
        for device in self.devices(ecidset):
            # get all information returned for this device
            info = result.get(device.ecid, {})
            if info:
                # iterate the cache to find queries for this device
                for q, ecids in _cache.items():
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
                            # err = "missing query result: {0!r}: {1!r}"
                            # self.log.error(err.format(q, device.name))
                            self.log.error("missing query: %r: %s", q, device)

                    # TO-DO: should be handled elsewhere and not buried here
                    if q == 'installedApps':
                        # find and report any unknown apps
                        new = self.apps.unknown(device)
                        # only report if new apps were found
                        if new:
                            # TO-DO: design mechanism for tracking repeat installations
                            msg = u"NEW: {0!s}: {1!s}".format(device, new)
                            self.log.info(msg)
                            self.reporter.send(msg)
                        else:
                            # _msg = "{0!s}: no unknown apps found"
                            # self.log.debug(_msg.format(device))
                            self.log.debug("%s: no unknown apps", device)

            else:
                self.log.error("missing results for: %s", device)

        # cache should only be made up of failed (or un-run)
        # queries at this point
        # TO-DO: test cache removes successful queries
        for q, ecids in _cache.items():
            if ecids:
                msg = "run_queries: re-tasking query: {0!r}: {1!r}"
                self.log.debug(msg.format(q, ecids))
                self.task.query(q, ecids)

        # forward along the results for processing elsewhere
        return result

    def erase(self, targets):
        """
        Erase devices and task for supervision and App installation 
        
        :param DeviceList targets:  devices to erase
        :returns: None
        """
        # get subset of device ECIDs that need to be erased
        tasked_ecids = self.task.erase(only=targets.ecids)
        
        if not tasked_ecids:
            self.log.info("no devices need to be erased")
            return

        # update device record before erase (or will count as checkout)
        tasked = self.devices(tasked_ecids)
        for device in tasked:
            self.log.debug("erase: found device: %s", device)
            device.restarting = True
            device.delete('erased')
        
        erased = []
        failed = []
        try: 
            self.verified = False
            self.log.info("erasing devices: %s", tasked)
            result = cfgutil.erase(tasked.ecids, self.authorization())
            erased = self.devices(result.ecids)
            failed = self.devices(result.missing)
        except cfgutil.FatalError as e:
            # no device was erased
            self.log.exception("failed to erase devices")
            if "complete the activation process" in e.message:
                # handle devices that are activation locked
                _locked = self.devices(e.affected)
                err = "activation locked: {0}".format(_locked.names)
                self.log.error(err)
                self.reporter.send(err)
                # TO-DO: still need a way of separating these systems
            raise
        except cfgutil.CfgutilError as e:
            # some devices were erased (continue with working devices)
            self.log.error("partial erase failure")
            erased = self.devices(e.unaffected)
            failed = self.devices(e.affected)
            self.log.debug("unaffected devices: %s", erased)
            self.log.error("affected devices: %s", failed)
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
                # un-mark failed devices as restarting
                for d in devices:
                    d.restarting = False
            else:
                self.log.debug("all devices were successfully erased!")
                
            if erased:
                self.log.info("succesfully erased: %s", erased)
                # process erased devices
                # task devices for supervision and app installation
                self.task.prepare(erased.ecids)
                
                for device in erased:
                    _installapps = self.apps.list(device)
                    if _installapps:
                        self.task.installapps([device.ecid])
                    else:
                        self.log.info("no apps to install for %s", device)
                        
                now = dt.datetime.now()
                for device in erased:
                    device.erased = now
                    
                self.task.add('restart', erased.ecids)
                self.stop(reason='restart')
                
    def supervise(self, targets):
        """
        Supervise devices

        :param DeviceList targets:  devices to supervise
        :returns: None
        """
        # Check if manager has been stopped
        if self.stopped:
            raise Stopped("supervision was stopped")

        # only continue with unsupervised devices
        unsupervised = targets.unsupervised
        tasked_ecids = self.task.prepare(only=unsupervised.ecids)                

        if not tasked_ecids:
            self.log.info("no devices need to be supervised")
            return

        # make sure device network checks out
        tasked = self.devices(tasked_ecids)
        try:
            self.check_network(tasked, tethered=True)
        except tethering.Error:
            self.log.error("unable to use tethering")
            self.check_network(tasked, tethered=False)
    
        prepared, failed = [], []
        try:
            self.log.info("preparing devices: %s", tasked)
            self.verified = False
            result = cfgutil.prepareDEP(tasked.ecids)
            prepared = self.devices(result.ecids)
            failed = self.devices(result.missing)

        except cfgutil.CfgutilError as e:
            self.log.exception("supervision partially failed")
            prepared = self.devices(e.unaffected)
            failed = self.devices(e.affected)
            self.log.info("attempting to continue with: %s", prepared)

        except cfgutil.FatalError as e:
            self.log.error("supervision failed: %s", e)
            if "must be erased" in e.message:
                err = "erroneously attempted to re-supervise device(s)"
                self.log.debug(err)
            elif e.detail == "Network communication error.":
                self.log.debug("Network unavailable")
            else:
                self.log.exception("unexpected fatal error", e)
                self.log.error(e.detail)
                raise

        except Exception:
            self.log.exception("unexpected error occurred")
            raise

        finally:
            if failed:
                # failed devices will be re-tasked during finalize()
                self.log.error("failed to prepare: %s", failed)
            # TO-DO: REVISIT
            # re-query supervision for ALL devices (handled by verification)
            # self.task.query('isSupervised', tasked.ecids)

            # any devices that remain unsupervised will be re-tasked
            #   during verification
            if prepared:
                self.log.info("successfully supervised: %s", prepared)
                for device in prepared:
                    # not sure this is being used anymore
                    device.enrolled = dt.datetime.now()
                    device.supervised = True
                
                # tethering now requires device restart (weird behaviour)
                # if tethering.enabled():
                    # self.log.debug("restarting devices for tethering")
                    # self.restart(prepared)
            else:
                self.log.error("no devices were supervised")
            
    def restart(self, devices):
        """
        Restart devices and stop automation

        :param DeviceList targets:  devices to restart
        :returns: None
        """
        self.log.info("restarting devices: %s", devices)
        self.task.add('restart', devices.ecids)
        for device in devices:
            device.restarting = True
        cfgutil.restart(devices.ecids, self.authorization())        
        self.stop(reason='restart')

    def shutdown(self, devices):
        """
        Shutdown devices using actools.cfgutil

        :param DeviceList targets:  devices to shutdown
        :returns: None
        """
        if devices:
            self.log.info("shutting down devices: %s", devices)
            cfgutil.shutdown(devices.ecids, self.authorization())
        else:
            self.log.debug("no devices specified")

    def installapps(self, targets):
        """
        Pass off App installation to aeios.apps.AppManager

        :param DeviceList targets:  devices to install Apps
        :returns: None
        """
        # Check if manager has been stopped
        if self.stopped:
            raise Stopped("skipped app installation")

        # get the ECIDs of the devices tasked for app installation
        tasked_ecids = self.task.installapps(only=targets.ecids)
        if not tasked_ecids:
            self.log.debug("no devices tasked for app installation")
            return
        tasked = self.devices(tasked_ecids)

        # Hacky hook (until something better can be figured out)
        if self._install_local_apps:
            self.apps.install_local_apps(tasked)

        try:
            self.apps.install_vpp_apps(tasked)
        except apps.RecoveryError as e:
            alert = e.alert
            # TO-DO: skip app verification
            details = u"{0}: {1!r} ({2!r})".format(alert.details,
                                                  alert.choices, 
                                                  alert.options)
            self.reporter.send(u"{0!s}".format(details))
            raise

    def set_background(self, targets, _type):
        """
        Set device wallpaper

        :param DeviceList targets:  devices to modify wallpaper 
        :param string _type:        name of image to use

        :returns: None
        """
        # TO-DO: stop setting alert for unverified devices
        #        Alert should only be set in emergency situations:
        #           - Data not removed
        #           - Unable to erase
        #           - more?
        # - change _type to name
        
        if self.stopped:
            raise Stopped("set_background")

        if not targets:
            self.log.error("no devices specified")
            return

        if not self.images:
            self.log.error("no images available")
            return

        if targets.unsupervised:
            err = "cannot modify wallpaper for unsupervised devices"
            self.log.error(err + ": %s", targets.unsupervised)

        # background cannot be set on unsupervised devices
        tasked = targets.supervised
        if not tasked:
            self.log.error("no wallpapers modified")
            return

        images = {}
        for image in os.listdir(self.images):
            name, ext = os.path.splitext(image)
            if ext in ['.png', '.jpeg', '.jpg']:
                path = os.path.join(self.images, image)
                images[name] = path
        
        try:
            image = images[_type]
            result = cfgutil.wallpaper(tasked.ecids, image,
                                       self.authorization())
            for device in self.devices(result.ecids):
                device.background = _type
        except cfgutil.CfgutilError as e:
            self.log.exception("failed to set background: %s", tasked)
            self.log.debug("unaffected: %s", e.unaffected)
            self.log.debug("affected: %s", e.affected)
            raise
        except KeyError as e:
            self.log.error("no image for: {0}".format(e))
            return

    def load_balance(self):
        """
        Shutdown verified devices
        
        NOTE:
            meant to balance the number of devices to mitigate odd behavior 
            when the USB bus is overloaded (typically around 10 devices)
        """
        # wishlist
        # if self.enabled('load balancing'):
        balanced = self.config.get('loadBalancing')
        self.log.debug("load balance: %r", balanced)
        if balanced:
            self.log.debug("load balancing: ENABLED")
            available = self.available()
            count = len(available)
            if count > balanced:
                self.log.debug("balancing: %d devices", count)
                _verified = available.verified
                self.log.debug("shutting down devices: %s", _verified)
                self.shutdown(_verified)
            else:
                self.log.debug("load is already balanced: %d", count)
        else:
            self.log.debug("load balancing: DISABLED")
        
    @property
    def verified(self):
        """
        :returns: verification status
        (reset by checkin, checkout, erase, supervise, and installapps)
        """
        _verified = self.config.setdefault('verified', False)
        if not _verified:
            try:
                self.config.delete('verification')
            except KeyError:
                pass
        return _verified

    @verified.setter
    def verified(self, value):        
        if not isinstance(value, bool):
            raise TypeError("{0}: not boolean".format(value))
        _data = {'verified': value}
        if value: 
            _data['verification'] = dt.datetime.now()
        self.config.update(_data)
    
    def _verify(self):
        """
        Run significant verification
        >>> if not self.verified:
        >>>     # do something
        
        NOTE: I would like to change this in the future, but should work
              relatively well for now 
        """
        self.log.debug("running significant verification")
                    
        # get all available devices
        available = self.available()
        # Re-query supervision and apps on all available devices
        self.task.query('installedApps', available.ecids)
        self.task.query('isSupervised', available.ecids)
        self.run_queries()
        
        now = dt.datetime.now()
        retask = {}
        app_check = DeviceList()
        for device in available:
            _verified = True
            self.log.info("verifying: %s", device)
            
            # Fix device restart (handled by device)
            # checkin = now - device.checkin
            # if device.restarting and checkin > dt.timedelta(seconds=300):
            #     self.log.error('%s: incorrectly restarting', device)
            #     device.restarting = False

            # verify device Serial Number
            if not device.serialnumber:
                device.verified = False
                self.log.error('%s: missing serial number', device)
                self.task.query('serialNumber', [device.ecid])
            else:
                self.log.debug('%s: has serial number!', device)

            # verify device was erased
            unknown_apps = self.apps.unknown(device)
            if not device.erased or unknown_apps:
                if not device.erased:
                    self.log.error("%s: never erased...", device)
                elif unknown_apps:
                    self.log.error("%s: unknown apps found...", device)
                _erasetask = retask.setdefault('erase', [])
                _erasetask.append(device.ecid)
                self.log.debug(" ... skipping additional verification")
                device.verified = False
                continue
            else:
                self.log.debug("%s: erase verified!", device)
                app_check.append(device)
                
            # verify device supervision
            if not device.supervised:
                device.verified = False
                _enrolltask = retask.setdefault('prepare', [])
                _enrolltask.append(device.ecid)
                self.log.error("%s: supervision failed...", device)
            else:
                self.log.debug("%s: supervision verified!", device)
            self.log.debug("%s: verified == %s", device, _verified)
            device.verified = _verified         

        # App Verification
        missing_apps = []
        try:
            missing_apps = self.apps.verify(app_check)
            if missing_apps:
                self.log.debug("found missing apps: %r", missing_apps)
                self.log.debug("ecids: %r", missing_apps.ecids)
                retask['installapps'] = missing_apps.ecids
        except apps.SkipVerification as e:
            self.log.error("unable to verify apps: %s", e)
            self.reporter.send(e)
            # re-check verification, but don't re-task app installation
            missing_apps = self.apps.verify(app_check, force=True)    
        finally:
            for d in missing_apps:
                d.verified = False
                
        # sanitize unavailable devices
        unavailable = DeviceList()
        for device in self.unavailable():
            if device.restarting:
                # ignore restarting devices
                self.log.info("%s: currently restarting", device)
                self.log.debug("ignoring %s", device)
                continue
            elif not device.checkout:
                # checkout unavailable devices
                self.log.error("%s: never checked out", device)
                device.checkout = now
            unavailable.append(device)
        
        self.task.remove(unavailable.ecids)

        # Re-Task Devices
        _verified = True
        self.log.debug("retasking: %r", retask)
        for name, ecids in retask.items():
            # if any tasks have to be added then verification failed
            retasked = set(ecids).difference(unavailable.ecids)
            self.log.debug("retasked: %r", retasked)
            if retasked:
                _verified = False
                self.log.debug("restasking: %r, %r", name, retasked)
                self.task.add(name, retasked)
                self.log.debug("retasked: %r, %r", name, retasked)
        
        self.log.debug("all devices verified: %s", _verified)
        return _verified
    
    def verify(self, run=False):
        """
        Quick verification
        runs more significant verification as necessary
        """
        with self.lock.acquire(timeout=-1):
            if self.stopped:
                # TO-DO: is there a reason I'm not raising Stopped()?
                # raise Stopped("verification")
                self.log.info("verification stopped")
                return

            # not sure what this does anymore, but removing it created
            # some odd behaviour
            last_run = self.config.get('finished')
            if last_run:
                _seconds = (dt.datetime.now() - last_run).seconds
                if _seconds < 60:
                    self.log.debug("ran less than 1 minute ago...")
                    return

            self.log.info("verifying automation")

            # Check for pending queries
            if self.task.queries():
                self.log.debug("found pending queries")
                self.verified = False
            else:
                self.log.debug("all queries completed!")
                
            # Check for pending tasks
            # NOTE: can return false positives if unavailable devices
            #       are tasked
            if not self.task.alldone():
                self.log.debug("found pending tasks")
                self.verified = False
            else:
                self.log.debug("all tasks completed!")
                
            # Check verification status
            if not self.verified:
                self.verified = self._verify()
        
            # re-check verification after self._verify()
            if not self.verified:
                self.log.info("verification failed...")
                if run:
                    self.log.debug("running automation")
                    self.run()
            else:
                self.log.info("all devices and tasks were verified!")
                # attempt to keep load balancing from happening too quickly
                # after app installation
                now = dt.datetime.now()
                timestamp = self.config.get('verification', now)
                vtimedelta = now - timestamp
                self.log.debug("verified for: %s", vtimedelta)
                if vtimedelta > dt.timedelta(minutes=5):
                    self.load_balance()
                else:
                    self.log.debug("load balancing skipped")

    def finalize(self):
        """
        Redundant finalization checks, verify tasks completed,
        and adjust backgrounds of supervised devices
        """
        self.log.debug("finalizing devices")
        if self.stopped:
            raise Stopped("finalization")

        # run verification
        self.verify()
        
        # Check tasks for any re-tasked devices
        _retasked = set()
        if not self.verified:
            for k, v in self.task.record.items():
                if v:
                    _retasked.update(v)
                    self.log.debug("retasked: %s: %s", k, v)
        
        _wallpapers = {'alert': DeviceList(), 
                       'background': DeviceList()}

        # Find devices that need wallpaper
        for d in self.available():
            # if d.ecid in _retasked:
            #     if d.background != 'alert':
            #         _wallpapers['alert'].append(d)
            # elif d.background != 'background':
            #     _wallpapers['background'].append(d)
            if d.ecid not in _retasked and d.background != 'background':
                _wallpapers['background'].append(d)

        for image, _devices in _wallpapers.items():
            if _devices:
                try:
                    self.set_background(_devices, image)
                except cfgutil.Error as e:
                    self.log.error("wallpaper failed: %r: %s", image, e)
        
        # update finishing timestamp            
        self.config.update({'finished': dt.datetime.now()})
        self.log.debug("finalization complete")
      
    def run(self):
        """
        Run automation
        """
        # keep multiple managers from running simultaneously
        #   (will be changed in future version)
        with self.lock.acquire(timeout=-1):
            self.log.info("running automation")
            if self.stopped:
                self.log.info("automation stopped")
                return

            # if something triggered run(), verification is lost
            self.verified = False

            if self.task.alldone() and self.verified:
                self.log.info("all tasks have been completed")
                # self.finalize()
                # exit early if no tasks exist
                return
            else:
                # log all tasks by name and ECIDs
                for k, v in self.task.record.items():
                    if v:
                        # only print tasks that are on the agenda
                        self.log.info("tasked: %s: %s", k, v)

            # Pre-Automation (queries)
            # give lagging devices a chance to catch up
            time.sleep(5)
            self.run_queries()
            
            devices = self.available()
            self.log.debug("available: %s", devices)
            
            # Automation
            try:
                self.erase(devices)
                self.supervise(devices)
                self.installapps(devices)
            except Stopped as e:
                self.log.info(e)
                return

            # Finalization
            self.finalize()
            self.log.info("automation finished")


if __name__ == '__main__':
    pass
