# -*- coding: utf-8 -*-

import logging
from datetime import datetime

import config
from actools import cfgutil

'''Persistant iOS device record
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '2.0.1'
__url__ = None
__description__ = 'Persistant iOS device record'
__all__ = ['Device', 'DeviceError']

## CHANGELOG:
# 2.0.1:
#   - added generic timestamp setter

class Error(Exception):
    pass


class DeviceError(Error):
    pass


class Device(object):

    def __init__(self, udid, info={}, logger=None, **kwargs):
        _info = info.copy()
        _udid = _info.get('UDID')
        if udid and _udid and _udid != udid:
            raise DeviceError("UDID mismatch")

        if not _info.setdefault('UDID', udid):
            raise DeviceError("missing device UDID")

        if not logger:
            logger = logging.getLogger(__name__)
            logger.addHandler(logging.NullHandler())
        self.log = logger

        self.config = config.Manager(udid, **kwargs)
        self.file = self.config.file
        
        try:
            self._record = self.config.read()
        except config.ConfigError:
            self.log.debug("record missing: creating new record")
            self.config.write(_info)
            self._record = self.config.read()
        except Exception as e:
            self.log.error("unknown error: {0!s}".format(e))
            raise DeviceError(str(e))

        # make sure non-changing values are what we expect them to be
        self._verify(_info)        
        
        updatekeys = ['deviceName', 'bootedState', 'buildVersion',
                      'firmwareVersion', 'locationID']
        # get k,v from info that are in updatekeys and are not None
        updated = {k:_info.get(k) for k in updatekeys}
        # only update non-null values
        self.config.update({k:v for k,v in updated.items() if v})

        # indelible attributes (if one is missing we are in bad shape)
        try:
            self._record = self.config.read()
            self.ecid = self._record['ECID']
            self.udid = self._record['UDID']
            self.model = self._record['deviceType']
        except KeyError as e:
            raise DeviceError("record missing key: {0}".format(e))
        self.serialnumber = self._record.get('serialNumber')
        self._testing = None

    def __str__(self):
        return self.name

    def _verify(self, info):
        '''verify device fidelity. 
        raise an Exception if ECID, deviceType, or serialNumber change
        '''
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
        '''Generic timestamp setter for various attributes
        '''
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

    @property
    def record(self):
        return self.config.read()

    @property
    def name(self):
        '''reads name from configuration file, if it is missing
        then the deviceName is given (as long as the device name)
        doesn't start with 'i' ('iPad (1)', 'iPad', 'iPhone')
        it is written to the configuration file
        '''
        _name = self.config.get('name')
        if not _name:
            self.log.debug("no name was found...")
            _name = self.config.get('deviceName', _name)
            # default 'iPhone', 'iPad', etc
            if _name and not _name.startswith('i'):
                self.log.debug('saving name: {0}'.format(_name))
                self.config.update({'name': _name})
        return _name

    @name.setter
    def name(self, new):
        '''Uses cfgutil to rename device
        '''
        if self.name != new:
            if not self._testing:
                cfgutil.rename(self.ecid, new)
            self.config.update({'name': new})

    @property
    def restarting(self):
        return self.config.setdefault('restarting', False)

    @restarting.setter
    def restarting(self, value):
        self.log.debug("{0!s} marking restart: {1}".format(self, value))
        if not isinstance(value, bool):
            raise TypeError("{0}: not boolean".format(value))
        self.config.update({'restarting': value})

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
    def erased(self):
        return self.config.get('erased')

    @erased.setter
    def erased(self, timestamp):
        self._timestamp('erased', timestamp)
        self.config.deletekeys(['background', 'apps', 'enrolled'])

    @property
    def locked(self):
        return self.config.get('locked')

    @locked.setter
    def locked(self, timestamp):
        self._timestamp('locked', timestamp)

    @property
    def apps(self):
        return self.config.setdefault('apps', [])

    @apps.setter
    def apps(self, applist):
        if not isinstance(applist, list):
            raise TypeError("{0}: not list".format(applist))
        self.config.reset('apps', applist)
    
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
