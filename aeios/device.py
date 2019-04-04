# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta

import config
from actools import cfgutil

"""
Persistant iOS Device Record
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "2.7.0"
__all__ = ['Device', 'DeviceError', 'DeviceList']

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())


class Error(Exception):
    pass


class DeviceError(Error):
    pass


class DeviceList(list):
    """
    convenience class for getting singular property from multiple devices
    at once
    """
    @property
    def ecids(self):
        """
        :returns: list of device ECIDs
        """
        return [x.ecid for x in self]
    
    @property
    def serialnumbers(self):
        """
        :returns: list of device serial numbers
        """
        return [x.serialnumber for x in self]
    
    @property
    def udids(self):
        """
        :returns: list of device UDIDs
        """
        return [x.udid for x in self]
    
    @property
    def names(self):
        """
        :returns: list of device names
        """
        return [x.name for x in self]

    @property
    def verified(self):
        """
        :returns: DeviceList of verified devices
        """
        return DeviceList([x for x in self if x.verified])

    @property
    def unverified(self):
        """
        :returns: DeviceList of un-verified devices
        """
        return DeviceList([x for x in self if not x.verified])

    @property
    def supervised(self):
        """
        :returns: DeviceList of supervised devices
        """
        return DeviceList([x for x in self if x.supervised])

    @property
    def unsupervised(self):
        """
        :returns: DeviceList of un-supervised devices
        """
        return DeviceList([x for x in self if not x.supervised])

    def __repr__(self):
        """
        'DeviceList(name, name2, ...)'
        """
        return "DeviceList({0})".format(self.names)

    def __str__(self):
        """
        comma separated names per device e.g. 'name, name2, ...'
        """
        return ", ".join(self.names)
    
    def __eq__(self, x):
        if len(self) == len(x):
            return sorted(self.ecids) == sorted(x.ecids)
        else:
            return False


class Device(object):

    def __init__(self, ecid, info=None, **kwargs):
        self.log = logging.getLogger(__name__)

        self.config = config.Manager(ecid, **kwargs)
        self.file = self.config.file

        try:
            self._record = self.config.read()
        except config.Error:
            if not info:
                raise DeviceError("missing device information")
            self.config.write(info)
            self._record = self.config.read()
        except Exception as e:
            self.log.exception("unknown error occurred")
            raise DeviceError(e)

        if info:
            # verify unchanging values
            self._verify(info)
            # if device info was provided, let's update the record
            updatekeys = ['deviceName', 'bootedState', 'buildVersion',
                          'firmwareVersion', 'locationID']
            # get k,v from info that are in updatekeys and are not None
            updated = {k: info.get(k) for k in updatekeys}
            # only update non-null values
            self.config.update({k: v for k, v in updated.items() if v})

        # indelible attributes (if one is missing we are in bad shape)
        try:
            self._record = self.config.read()
            self.ecid = self._record['ECID']
            self.udid = self._record['UDID']
            self.model = self._record['deviceType']
        except KeyError as e:
            raise DeviceError("record missing key: {0}".format(e))
        self.serialnumber = self._record.get('serialNumber')

    def __str__(self):
        return self.name

    def _verify(self, info):
        """
        Verify device fidelity

        :raises: DeviceError if ECID, deviceType, or serialNumber change
        """
        for k in ['ECID', 'deviceType', 'serialNumber']:
            try:
                p = info[k]
                r = self._record[k]
                if p != r:
                    err = ("static device key mismatch: " 
                           "{0!r} != {1!r}".format(r, p))
                    raise DeviceError(err)
            except KeyError:
                pass

    def _timestamp(self, key, value):
        """
        Generic timestamp setter for various attributes
        """
        if value is not None:
            if not isinstance(value, datetime):
                raise TypeError("invalid datetime: {0}".format(value))
            self.config.update({key: value})
        else:
            return self.delete(key)

    def delete(self, key):
        try:
            return self.config.delete(key)
        except:
            return None

    def update(self, key, value):
        _attrmap = {'serialNumber': 'serialnumber'}
        attribute = _attrmap.get(key)
        if attribute:
            setattr(self, attribute, value)
        self.config.update({key: value})

    def updateall(self, info):
        _attrmap = {'serialNumber': 'serialnumber'}
        for k, a in _attrmap.items():
            if k in info.keys():
                setattr(self, a, info[k])
        self.config.update(info)
        
    @property
    def verified(self):
        return self.config.setdefault('verified', False)
    
    @verified.setter
    def verified(self, value):
        if not isinstance(value, bool):
            raise TypeError("{0}: not boolean".format(value))
        self.config.update({'verified': value})

    @property
    def record(self):
        return self.config.read()

    @property
    def name(self):
        """
        reads name from configuration file, if it is missing
        then the deviceName is given (as long as the device name)
        doesn't start with 'i' ('iPad (1)', 'iPad', 'iPhone')
        it is written to the configuration file
        """
        _name = self.config.get('name')
        if not _name:
            self.log.debug("no name was found...")
            _name = self.config.get('deviceName', _name)
            # default 'iPhone', 'iPad', etc
            if _name and not _name.startswith('i'):
                self.log.debug('saving name: {0}'.format(_name))
                self.config.update({'name': _name})
            else:
                _name += " ({0})".format(self.ecid)
        return _name

    @name.setter
    def name(self, new):
        """
        Rename devices using actools.cfgutil
        """
        if self.name != new:
            if not self._testing:
                cfgutil.rename(self.ecid, new)
            self.config.update({'name': new})

    @property
    def restarting(self):
        _restarting = self.config.setdefault('restarting', False)
        if _restarting:
            restarted = self.config.get('restarted')
            try: 
                if (datetime.now() - restarted) > timedelta(minutes=5):
                    self.restarting = False
                    _restarting = False
            except TypeError:
                self.restarting = False
                _restarting = False
        return _restarting

    @restarting.setter
    def restarting(self, value):
        if not isinstance(value, bool):
            raise TypeError("{0}: not boolean".format(value))
        _value = {'restarting': value}
        if value:
            # mark the time the device was restarted
            _value['restarted'] = datetime.now()
        self.config.update(_value)

    @property
    def enrolled(self):
        return self.config.get('enrolled')

    @enrolled.setter
    def enrolled(self, timestamp):
        self._timestamp('enrolled', timestamp)

    @property
    def checkin(self):
        return self.config.get('checkin')

    @checkin.setter
    def checkin(self, timestamp):
        self._timestamp('checkin', timestamp)

    @property
    def checkout(self):
        return self.config.get('checkout')

    @checkout.setter
    def checkout(self, timestamp):
        self._timestamp('checkout', timestamp)

    @property
    def supervised(self):
        return self.config.setdefault('isSupervised', False)

    @supervised.setter
    def supervised(self, value):
        if not isinstance(value, bool):
            raise TypeError('not boolean: {0}'.format(value))
        self.config.update({'isSupervised': value})

    @property
    def erased(self):
        return self.config.get('erased')

    @erased.setter
    def erased(self, timestamp):
        self._timestamp('erased', timestamp)
        _reset = ['background', 'apps', 'enrolled', 'isSupervised', 
                  'installedApps', 'verified']
        self.config.deletekeys(_reset)

    @property
    def locked(self):
        return self.config.get('locked')

    @locked.setter
    def locked(self, timestamp):
        self._timestamp('locked', timestamp)

    @property
    def apps(self):
        return self.config.setdefault('installedApps', [])

    @apps.setter
    def apps(self, applist):
        try:
            self.config.reset('installedApps', list(applist))
        except:
            self.config.update({'installedApps': applist})
    
    @property
    def background(self):
        return self.config.get('background')

    @background.setter
    def background(self, name):
        if name:
            if not isinstance(name, str):
                raise TypeError("invalid background: {0}".format(name))
            self.config.update({'background': name})
        else:
            try:
                self.config.delete('background')
            except:
                pass


if __name__ == '__main__':
    pass
