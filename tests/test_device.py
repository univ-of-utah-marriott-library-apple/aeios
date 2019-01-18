#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import unittest
import plistlib
import threading
from datetime import datetime, timedelta

'''Tests for ipadmanager.device
'''

## import modules to test
from device import Device, DeviceError
from config import FileLock

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '1.0.3'
__url__ = None
__description__ = 'Tests for ipadmanager.device'

## location for temporary files created with tests
TMPDIR = os.path.join(os.path.dirname(__file__), 'tmp')

def setUpModule():
    '''create tmp directory
    '''
    try:
        os.mkdir(TMPDIR)
    except OSError as e:
        if e.errno != 17:
            # raise Exception unless TMP already exists
            raise
    
def tearDownModule():
    '''remove tmp directory
    '''
    shutil.rmtree(TMPDIR)


class TestNewDeviceInit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        '''One time setup for this TestCase. 
        If Exception is raised, no tests are run.
        '''
        pass
        
    @classmethod
    def tearDownClass(cls):
        '''One time cleanup for this TestCase. 
        Skipped if setUpClass raises an Exception
        '''
        pass

    def setUp(self):
        '''Runs before each test.
        '''
        self.path = os.path.join(TMPDIR, 'new')
        self.info = {'locationID':'0x00000001',
                     'UDID':'a0111222333444555666777888999abcdefabcde',
                     'ECID': '0x123456789ABCD0',
                     "name":"checkout-ipad-1",
                     "deviceType":"iPad7,5"}
        udid = self.info['UDID']
        self.udid = udid
        self.file = os.path.join(self.path, "{0}.plist".format(udid))
        # self.device = Device(id='init_test', path=self.path)

    def tearDown(self):
        '''remove the device record file after each run
        '''
        try:
            os.remove(self.file)
        except OSError as e:
            if e.errno != 2:
                raise
    
    def test_minimal_init_succeeds(self):
        min = {k:self.info.get(k) for k in ['ECID','deviceType']}
        d = Device(self.udid, info=min, path=self.path)

    def test_minimal_init_not_modified(self):
        min = {k:self.info.get(k) for k in ['ECID','deviceType']}
        d = Device(self.udid, info=min, path=self.path)
        with self.assertRaises(KeyError):
            min['UDID']

    def test_init_duplicate_udid(self):
        min = {k:self.info.get(k) for k in ['ECID','deviceType','UDID']}
        d = Device(self.udid, info=min, path=self.path)

    def test_alternative_minimal_init_succeeds(self):
        min = {k:self.info.get(k) for k in ['UDID','ECID','deviceType']}
        d = Device(None, info=min, path=self.path)

    def test_alternative_minimal_init_fails_missing_udid(self):
        min = {k:self.info.get(k) for k in ['ECID','deviceType']}
        with self.assertRaises(DeviceError):
            Device(None, info=min, path=self.path)

    def test_init_fails_missing_info(self):
        with self.assertRaises(DeviceError):
            d = Device(self.udid, path=self.path)

    def test_minimal_init_fails_missing_ecid(self):
        min = {'deviceType':self.info.get('deviceType')}
        with self.assertRaises(DeviceError):
            d = Device(self.udid, info=min, path=self.path)

    def test_minimal_init_fails_missing_deviceType(self):
        min = {'ECID':self.info.get('ECID')}
        with self.assertRaises(DeviceError):
            d = Device(self.udid, info=min, path=self.path)

    def test_device_record_created(self):
        min = {k:self.info.get(k) for k in ['ECID','deviceType']}
        d = Device(self.udid, info=min, path=self.path)
        self.assertTrue(os.path.exists(d.file))

    def test_device_record_has_keys(self):
        keys = ['UDID','ECID','deviceType']
        min = {k:self.info.get(k) for k in keys}
        d = Device(self.udid, info=min, path=self.path)
        for key,value in plistlib.readPlist(d.file).items():
            expected = self.info.get(key)
            self.assertEquals(expected, value)

    def test_device_record_has_all_keys(self):
        d = Device(self.udid, info=self.info, path=self.path)
        result = plistlib.readPlist(d.file)
        self.assertEquals(result, self.info)

    def test_device_record_no_extra_keys(self):
        d = Device(self.udid, info=self.info, path=self.path)
        result = plistlib.readPlist(d.file)
        for k in result.keys():
            self.assertIsNotNone(self.info.get(k))

    def test_device_udid_mismatch(self):
        min = {k:self.info.get(k) for k in ['ECID','deviceType','UDID']}
        incorrect = "{0}bad".format(self.udid)
        with self.assertRaises(DeviceError):
            Device(incorrect, info=min, path=self.path)


class TestExistingDeviceInit(unittest.TestCase):

    file = None
    @classmethod
    def tearDownClass(cls):
        '''One time cleanup for this TestCase. 
        Skipped if setUpClass raises an Exception
        '''
        try:
            os.remove(cls.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def setUp(self):
        '''Runs before each test.
        '''
        self.path = os.path.join(TMPDIR, 'existing')
        self.orig = {'ECID': '0x1D481C2E300026',
                     'UDID': 'fbe61f791f298c66ebb00a282f5b070c6cb9dc47',
                     'bootedState': 'Booted',
                     'buildVersion': '15E302',
                     'deviceName': 'test-student-checkout-ipad-2',
                     'deviceType': 'iPad7,5',
                     'firmwareVersion': '11.3.1',
                     'locationID': '0x14100000'}
        self.udid = self.orig.get('UDID')
        self.device = Device(self.udid, info=self.orig, 
                                    path=self.path)
        self.__class__.file = self.file = self.device.file

    def tearDown(self):
        '''remove the device record file after each run
        '''
        try:
            os.remove(self.file)
        except OSError as e:
            if e.errno != 2:
                raise
                
    def test_existing_record_initialized(self):
        Device(self.udid, path=self.path)

    def test_existing_record_no_info(self):
        d = Device(self.udid, path=self.path)
        for key,value in plistlib.readPlist(d.file).items():
            self.assertEquals(self.orig[key], value)

    def test_existing_record_updated(self):
        new = {'deviceName':'iPad', 'firmwareVersion':'12.0',
               'locationID':'0x14100001', 'buildVersion': '15E303'}
        d = Device(self.udid, info=new, path=self.path)
        
        result = plistlib.readPlist(d.file)
        for key,value in result.items():
            old = self.orig.get(key)
            expected = new.get(key, old)
            self.assertEquals(expected, value)

    def test_existing_record_updated2(self):
        new = {'deviceName':'iPad', 'firmwareVersion':'12.0',
               'locationID':'0x14100001', 'buildVersion': '15E303'}
        d = Device(self.udid, info=new, path=self.path)
        
        result = plistlib.readPlist(d.file)
        for k in new.keys():
            self.assertNotEqual(result[k], self.orig[k])

    def test_verify_mismatching_UDID(self):
        mismatch = {'UDID': 'mismatch'}
        with self.assertRaises(DeviceError):
            Device(self.udid, info=mismatch, path=self.path)

    def test_verify_mismatching_deviceType(self):
        mismatch = {'deviceType': 'mismatch'}
        with self.assertRaises(DeviceError):
            Device(self.udid, info=mismatch, path=self.path)

    def test_verify_mismatching_ECID(self):
        mismatch = {'ECID': 'mismatch'}
        with self.assertRaises(DeviceError):
            Device(self.udid, info=mismatch, path=self.path)


class TestDeviceState(unittest.TestCase):

    file = None
    @classmethod
    def tearDownClass(cls):
        '''One time cleanup for this TestCase. 
        Skipped if setUpClass raises an Exception
        '''
        try:
            os.remove(cls.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def setUp(self):
        '''Runs before each test.
        '''
        self.path = os.path.join(TMPDIR, 'state')
        now = datetime.now()
        self.orig = {'ECID': '0x123456789ABCD0',
                     'UDID': 'a0111222333444555666777888999abcdefabcde',
                     'bootedState': 'Booted',
                     'buildVersion': '15E302',
                     'apps': ['app1', 'app2', 'app3'],
                     'background': 'background.png',
                     'erased': now - timedelta(seconds=3),
                     'enrolled': now - timedelta(seconds=2),
                     'checkout': now - timedelta(seconds=1),
                     'checkin': now,
                     'deviceName': 'checkout-ipad-1',
                     'name': 'checkout-ipad-1',
                     'deviceType': 'iPad7,5',
                     'firmwareVersion': '11.3.1',
                     'locationID': '0x00000001'}
        self.udid = self.orig.get('UDID')
        self.device = Device(self.udid, info=self.orig, 
                                    path=self.path)
        self.__class__.file = self.file = self.device.file

    def tearDown(self):
        '''remove the device record file after each run
        '''
        try:
            os.remove(self.file)
        except OSError as e:
            if e.errno != 2:
                raise
                
    def test_erase_removes_other_keys(self):
        keys = ['enrolled', 'apps', 'background']
        r = self.device.record
        for k in keys:
            self.assertTrue(r.has_key(k))
        self.device.erased = datetime.now()
        r = self.device.record
        for k in keys:
            self.assertFalse(r.has_key(k))
    
    def test_checkout(self):
        now = datetime.now().replace(microsecond=0)
        self.device.checkout = now
        self.assertEquals(self.device.checkout, now)

    def test_checkin(self):
        now = datetime.now().replace(microsecond=0)
        self.device.checkin = now
        self.assertEquals(self.device.checkin, now)

    def test_erased(self):
        now = datetime.now().replace(microsecond=0)
        self.device.erased = now
        self.assertEquals(self.device.erased, now)

    def test_enrolled(self):
        now = datetime.now().replace(microsecond=0)
        self.device.enrolled = now
        self.assertEquals(self.device.enrolled, now)


class TestDeviceName(unittest.TestCase):

    file = None
    @classmethod
    def tearDownClass(cls):
        '''One time cleanup for this TestCase. 
        Skipped if setUpClass raises an Exception
        '''
        try:
            os.remove(cls.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def setUp(self):
        '''Runs before each test.
        '''
        self.path = os.path.join(TMPDIR, 'name')
        self.info = {'ECID': '0x123456789ABCD0',
                     'UDID': 'a0111222333444555666777888999abcdefabcde',
                     'bootedState': 'Booted',
                     'buildVersion': '15E302',
                     'deviceName': 'checkout-ipad-1',
                     'deviceType': 'iPad7,5',
                     'firmwareVersion': '11.3.1',
                     'locationID': '0x00000001'}
        self.udid = self.info.get('UDID')
        self.device = Device(self.udid, info=self.info, 
                                    path=self.path)
        self.device._testing = True
        self.__class__.file = self.file = self.device.file

    def tearDown(self):
        '''remove the device record file after each run
        '''
        try:
            os.remove(self.file)
        except OSError as e:
            if e.errno != 2:
                raise
                
    def test_get_name(self):
        expected = self.info['deviceName']
        self.assertEquals(self.device.name, expected)

    def test_set_name(self):
        self.device.name = 'test'
        result = self.device.record
        self.assertEquals(self.device.name, result['name'])

    def test_getting_name_sets_name(self):
        expected = self.info['deviceName']
        name = self.device.name
        result = self.device.record
        self.assertEquals(result['name'], expected)

    def test_default_name_missing(self):
        result = self.device.record
        with self.assertRaises(KeyError):
            name = result['name']

    def test_new_device_name_does_not_affect_name(self):
        name = self.device.name
        _info = {'deviceName': 'iPad'}
        d = Device(self.udid, info=_info, path=self.path)
        result = self.device.record
        self.assertNotEqual(result['name'], result['deviceName'])


class TestDeviceRestarting(unittest.TestCase):

    file = None
    @classmethod
    def tearDownClass(cls):
        '''One time cleanup for this TestCase. 
        Skipped if setUpClass raises an Exception
        '''
        try:
            os.remove(cls.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def setUp(self):
        '''Runs before each test.
        '''
        self.path = os.path.join(TMPDIR, 'restarting')
        self.info = {'ECID': '0x123456789ABCD0',
                     'UDID': 'a0111222333444555666777888999abcdefabcde',
                     'bootedState': 'Booted',
                     'buildVersion': '15E302',
                     'deviceName': 'checkout-ipad-1',
                     'deviceType': 'iPad7,5',
                     'firmwareVersion': '11.3.1',
                     'locationID': '0x00000001'}
        self.udid = 'a0111222333444555666777888999abcdefabcde'
        self.device = Device(self.udid, info=self.info, 
                                    path=self.path)
        self.__class__.file = self.file = self.device.file

    def tearDown(self):
        '''remove the device record file after each run
        '''
        try:
            os.remove(self.file)
        except OSError as e:
            if e.errno != 2:
                raise
                
    def test_restarting_empty_by_default(self):
        result = self.device.record
        with self.assertRaises(KeyError):
            t = result['restarting']

    def test_restarting_empty_returns_false(self):
        result = self.device.record
        with self.assertRaises(KeyError):
            t = result['restarting']
        self.assertFalse(self.device.restarting)

    def test_restarting_sets_default(self):
        restarting = self.device.restarting
        result = self.device.record
        self.assertFalse(result['restarting'])

    def test_set_restarting(self):
        self.device.restarting = True
        result = self.device.record
        self.assertTrue(result['restarting'])


class TestDeviceEnrolled(unittest.TestCase):

    file = None
    @classmethod
    def tearDownClass(cls):
        '''One time cleanup for this TestCase. 
        Skipped if setUpClass raises an Exception
        '''
        try:
            os.remove(cls.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def setUp(self):
        '''Runs before each test.
        '''
        self.path = os.path.join(TMPDIR, 'enrolled')
        self.info = {'ECID': '0x123456789ABCD0',
                     'UDID': 'a0111222333444555666777888999abcdefabcde',
                     'bootedState': 'Booted',
                     'buildVersion': '15E302',
                     'deviceName': 'checkout-ipad-1',
                     'deviceType': 'iPad7,5',
                     'firmwareVersion': '11.3.1',
                     'locationID': '0x00000001'}
        self.udid = 'a0111222333444555666777888999abcdefabcde'
        self.device = Device(self.udid, info=self.info, 
                                    path=self.path)
        self.__class__.file = self.file = self.device.file

    def tearDown(self):
        '''remove the device record file after each run
        '''
        try:
            os.remove(self.file)
        except OSError as e:
            if e.errno != 2:
                raise
                
    def test_enrolled_empty_by_default(self):
        result = self.device.record
        with self.assertRaises(KeyError):
            t = result['enrolled']

    def test_enrolled_empty_returns_None(self):
        result = self.device.record
        with self.assertRaises(KeyError):
            t = result['enrolled']
        self.assertIsNone(self.device.enrolled)

    def test_set_datetime(self):
        self.device.enrolled = datetime.now()
        result = self.device.record
        self.assertIsNotNone(result['enrolled'])

    def test_set_enrolled_boolean(self):
        with self.assertRaises(TypeError):
            self.device.enrolled = True


class TestDeviceCheckin(unittest.TestCase):

    file = None
    @classmethod
    def tearDownClass(cls):
        '''One time cleanup for this TestCase. 
        Skipped if setUpClass raises an Exception
        '''
        try:
            os.remove(cls.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def setUp(self):
        '''Runs before each test.
        '''
        self.path = os.path.join(TMPDIR, 'checkin')
        self.info = {'ECID': '0x123456789ABCD0',
                     'UDID': 'a0111222333444555666777888999abcdefabcde',
                     'bootedState': 'Booted',
                     'buildVersion': '15E302',
                     'deviceName': 'checkout-ipad-1',
                     'deviceType': 'iPad7,5',
                     'firmwareVersion': '11.3.1',
                     'locationID': '0x00000001'}
        self.udid = 'a0111222333444555666777888999abcdefabcde'
        self.device = Device(self.udid, info=self.info, 
                                    path=self.path)
        self.__class__.file = self.file = self.device.file

    def tearDown(self):
        '''remove the device record file after each run
        '''
        try:
            os.remove(self.file)
        except OSError as e:
            if e.errno != 2:
                raise
                
    def test_empty_by_default(self):
        result = self.device.record
        with self.assertRaises(KeyError):
            t = result['checkin']

    def test_enrolled_empty_returns_None(self):
        result = self.device.record
        with self.assertRaises(KeyError):
            t = result['checkin']
        self.assertIsNone(self.device.checkin)

    def test_set_datetime(self):
        self.device.checkin = datetime.now()
        result = self.device.record
        self.assertIsNotNone(result['checkin'])

    def test_set_boolean(self):
        with self.assertRaises(TypeError):
            self.device.checkin = True


class TestDeviceCheckout(unittest.TestCase):

    file = None
    @classmethod
    def tearDownClass(cls):
        '''One time cleanup for this TestCase. 
        Skipped if setUpClass raises an Exception
        '''
        try:
            os.remove(cls.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def setUp(self):
        '''Runs before each test.
        '''
        self.path = os.path.join(TMPDIR, 'checkin')
        self.info = {'ECID': '0x123456789ABCD0',
                     'UDID': 'a0111222333444555666777888999abcdefabcde',
                     'bootedState': 'Booted',
                     'buildVersion': '15E302',
                     'deviceName': 'checkout-ipad-1',
                     'deviceType': 'iPad7,5',
                     'firmwareVersion': '11.3.1',
                     'locationID': '0x00000001'}
        self.udid = 'a0111222333444555666777888999abcdefabcde'
        self.device = Device(self.udid, info=self.info, 
                                    path=self.path)
        self.__class__.file = self.file = self.device.file

    def tearDown(self):
        '''remove the device record file after each run
        '''
        try:
            os.remove(self.file)
        except OSError as e:
            if e.errno != 2:
                raise
                
    def test_empty_by_default(self):
        result = self.device.record
        with self.assertRaises(KeyError):
            t = result['checkout']

    def test_empty_returns_None(self):
        result = self.device.record
        with self.assertRaises(KeyError):
            t = result['checkout']
        self.assertIsNone(self.device.checkout)

    def test_set_datetime(self):
        self.device.checkout = datetime.now()
        result = self.device.record
        self.assertIsNotNone(result['checkout'])

    def test_set_boolean(self):
        with self.assertRaises(TypeError):
            self.device.checkout = True

   
class TestDeviceEraseProperty(unittest.TestCase):

    file = None
    @classmethod
    def setUpClass(cls):
        cls.now = datetime.now()

    @classmethod
    def tearDownClass(cls):
        '''One time cleanup for this TestCase. 
        Skipped if setUpClass raises an Exception
        '''
        try:
            os.remove(cls.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def setUp(self):
        '''Runs before each test.
        '''
        self.path = os.path.join(TMPDIR, 'checkin')
        self.now = self.__class__.now
        self.info = {'ECID': '0x123456789ABCD0',
                     'UDID': 'a0111222333444555666777888999abcdefabcde',
                     'bootedState': 'Booted',
                     'buildVersion': '15E302',
                     'apps': ['app1', 'app2', 'app3'],
                     'background': 'background.png',
                     'deviceName': 'checkout-ipad-1',
                     'name': 'checkout-ipad-1',
                     'enrolled': self.now,
                     'deviceType': 'iPad7,5',
                     'firmwareVersion': '11.3.1',
                     'locationID': '0x00000001'}
        self.udid = 'a0111222333444555666777888999abcdefabcde'
        self.device = Device(self.udid, info=self.info, 
                                    path=self.path)
        self.__class__.file = self.file = self.device.file

    def tearDown(self):
        '''remove the device record file after each run
        '''
        try:
            os.remove(self.file)
        except OSError as e:
            if e.errno != 2:
                raise
                
    def test_empty_by_default(self):
        result = self.device.record
        with self.assertRaises(KeyError):
            t = result['erased']

    def test_empty_returns_None(self):
        with self.assertRaises(KeyError):
            self.device.record['erased']
        self.assertIsNone(self.device.erased)

    def test_set_datetime(self):
        self.device.erased = datetime.now()
        self.assertIsNotNone(self.device.record['erased'])

    def test_set_None(self):
        self.device.erased = datetime.now()
        self.assertIsNotNone(self.device.record['erased'])
        self.device.erased = None
        with self.assertRaises(KeyError):
            erased = self.device.record['erased']
                
    def test_set_boolean(self):
        with self.assertRaises(TypeError):
            self.device.erased = True

    def test_set_removes_other_attributes(self):
        self.assertIsNotNone(self.device.background)
        self.assertIsNotNone(self.device.enrolled)
        self.assertEquals(self.info['apps'], self.device.apps)
        self.device.erased = self.now
        self.assertIsNone(self.device.background)
        self.assertIsNone(self.device.enrolled)
        self.assertEquals([], self.device.apps)


class TestDeviceLocked(unittest.TestCase):

    file = None
    @classmethod
    def tearDownClass(cls):
        '''One time cleanup for this TestCase. 
        Skipped if setUpClass raises an Exception
        '''
        try:
            os.remove(cls.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def setUp(self):
        '''Runs before each test.
        '''
        self.path = os.path.join(TMPDIR, 'checkin')
        self.info = {'ECID': '0x123456789ABCD0',
                     'UDID': 'a0111222333444555666777888999abcdefabcde',
                     'bootedState': 'Booted',
                     'buildVersion': '15E302',
                     'apps': ['app1', 'app2', 'app3'],
                     'background': 'background.png',
                     'deviceName': 'checkout-ipad-1',
                     'name': 'checkout-ipad-1',
                     'enrolled': datetime.now(),
                     'deviceType': 'iPad7,5',
                     'firmwareVersion': '11.3.1',
                     'locationID': '0x00000001'}
        self.udid = 'a0111222333444555666777888999abcdefabcde'
        self.device = Device(self.udid, info=self.info, 
                                    path=self.path)
        self.__class__.file = self.file = self.device.file

    def tearDown(self):
        '''remove the device record file after each run
        '''
        try:
            os.remove(self.file)
        except OSError as e:
            if e.errno != 2:
                raise
                
    def test_empty_by_default(self):
        with self.assertRaises(KeyError):
            self.device.record['locked']

    def test_empty_returns_None(self):
        result = self.device.record
        with self.assertRaises(KeyError):
            t = result['locked']
        self.assertIsNone(self.device.locked)

    def test_set_datetime(self):
        self.device.locked = datetime.now()
        result = self.device.record
        self.assertIsNotNone(result['locked'])

    def test_set_None(self):
        self.device.locked = datetime.now()
        self.assertIsNotNone(self.device.record['locked'])
        self.device.locked = None
        with self.assertRaises(KeyError):
            locked = self.device.record['locked']
                

    def test_set_boolean(self):
        with self.assertRaises(TypeError):
            self.device.locked = True


class TestThreaded(unittest.TestCase):
    '''Tests involving threading
    '''
    def setUp(self):
        '''Runs before each test.
        '''
        self.path = os.path.join(TMPDIR, 'threaded')
        self.info = {'locationID':'0x00000001',
                     'UDID':'a0111222333444555666777888999abcdefabcde',
                     'ECID': '0x123456789ABCD0',
                     "deviceType":"iPad7,5"}
        self.udid = 'a0111222333444555666777888999abcdefabcde'
        self.device = Device(self.udid, info=self.info, 
                                    path=self.path)
        self.device2 = Device(self.udid, path=self.path)
        self.device3 = Device(self.udid, path=self.path)
        
    def tearDown(self):
        '''Runs after each test.
        '''
        try:
            os.remove(self.device.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def test_threaded_update(self):
        '''test threaded devices update as expected
        '''
        
        # function for threading
        def threaded_update(d, k, v):
            d.update(k, v)
        t1 = threading.Thread(target=threaded_update, 
                              args=(self.device2,'name','d2'))
        t2 = threading.Thread(target=threaded_update, 
                              args=(self.device3, 'name', 'd3'))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEquals(self.device.name, 'd3')


class TestLocking(unittest.TestCase):

    def setUp(self):
        '''Runs before each test.
        '''
        cls = self.__class__
        self.path = os.path.join(TMPDIR, 'locking')
        self.info = {'ECID': '0x123456789ABCD0',
                     'UDID':'a0111222333444555666777888999abcdefabcde',
                     "deviceType":"iPad7,5"}
        self.udid = 'a0111222333444555666777888999abcdefabcde'
        self.device = Device(self.udid, info=self.info, path=self.path)
        self.lock = FileLock(self.device.config.lockfile, timeout=1)
        
    def test_device_locked(self):
        with self.lock.acquire():
            with self.assertRaises(DeviceError):
                d = Device(self.udid, path=self.path, timeout=0)
        

if __name__ == '__main__':
    unittest.main(verbosity=2)
