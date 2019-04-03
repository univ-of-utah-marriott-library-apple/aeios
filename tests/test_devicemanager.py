#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import unittest 
import logging
import types
from datetime import datetime, timedelta

from actools import cfgutil

'''Tests for ipadmanager.devicemanager
'''

import aeios

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '1.0.0'
__url__ = None
__description__ = 'Tests for ipadmanager.devicemanager'

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
    #shutil.rmtree(TMPDIR)
    pass


class BaseTestCase(unittest.TestCase):
    
    file = None
    tmp = TMPDIR
    logger = None

    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(__name__)
        cls.env = [{'ECID': '0x123456789ABCD0',
                    'UDID': 'a0111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'test-ipad-1',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000001'},
                   {'ECID': '0x123456789ABCD1',
                    'UDID': 'a1111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'test-ipad-2',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000002'},
                   {'ECID': '0x123456789ABCD2',
                    'UDID': 'a2111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'test-ipad-3',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000003'},
                   {'ECID': '0x123456789ABCD3',
                    'UDID': 'a3111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'test-ipad-4',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000004'},
                   {'ECID': '0x123456789ABCD4',
                    'UDID': 'a4111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'test-ipad-5',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000005'},
                   {'ECID': '0x123456789ABCD5',
                    'UDID': 'a5111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'test-ipad-6',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000006'},
                   {'ECID': '0x123456789ABCD6',
                    'UDID': 'a6111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'test-ipad-7',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000007'},
                   {'ECID': '0x123456789ABCD7',
                    'UDID': 'a7111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'test-ipad-8',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000008'},
                   {'ECID': '0x123456789ABCD8',
                    'UDID': 'a8111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'test-ipad-9',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000009'},
                   {'ECID': '0x123456789ABCD9',
                    'UDID': 'a9111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'test-ipad-10',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000010'}]
        
    @classmethod
    def tearDownClass(cls):
        # os.remove(cls.file)
        pass
        
    def setUp(self):
        id = 'edu.utah.mlib.test'
        self.path = self.__class__.tmp
        logging.basicConfig(level=logging.CRITICAL)
        self.manager = aeios.DeviceManager(id, path=self.path)
        self.env = self.__class__.env
        self.info = self.env
        self.now = datetime.now()
        self.devices = []
        self.__class__.file = self.manager.file
    
    def tearDown(self):
        self.logger.setLevel(logging.CRITICAL)


class TestCheckin(BaseTestCase):

    def test_checkin(self):
        for info in self.info:
            self.manager.checkin(info, run=False)


class TestCheckout(BaseTestCase):

    def test_never_checked_in(self):
        '''Test that a device that has never been checked in
        '''
        for info in self.info:
            self.manager.checkout(info)


class TestNeedsErase(BaseTestCase):
    '''Tests for detecting if a device needs to be erased
    '''
    
    def setUp(self):
        super(self.__class__, self).setUp()
        d = self.env[0]
        self.device = self.manager.device(d['ECID'], d)
        self.now = datetime.now()
    
    def test_unmanaged_device(self):
        '''test unmanaged devices will not be erased
        '''
        ## Object Method patching
        #  replace our manager's managed function with one that simply 
        #  returns False. The function will be reset on next setUp
        def _dummy(self, x):
            return False
        self.manager.managed = types.MethodType(_dummy, self.manager)

        self.assertFalse(self.manager.need_to_erase(self.device))

    def test_not_checkedin(self):
        '''test non-checkedin device will be erased
        '''
        self.device.checkin = None
        self.assertTrue(self.manager.need_to_erase(self.device))
        self.device.checkin = datetime.now()

    def test_restarting(self):
        '''test restarting device will be erased
        '''
        self.device.restarting = True
        self.assertFalse(self.manager.need_to_erase(self.device))
        
    def test_quick_disconnect(self):
        '''test devices that quickly disconnect and reconnect
        '''
        self.device.erased = self.now - timedelta(minutes=5)
        self.device.checking = self.now - timedelta(seconds=10)
        self.device.checkout = self.now
        self.device.restarting = False
        # self.logger.setLevel(logging.DEBUG)
        self.assertFalse(self.manager.need_to_erase(self.device))

    def test_not_erased(self):
        '''test devices that have not been erased will be
        '''
        self.device.erased = None
        # self.logger.setLevel(logging.DEBUG)
        self.assertTrue(self.manager.need_to_erase(self.device))

    def test_erased_more_than_timeout_with_blink(self):
        '''test device was erased but exceed the timeout
        '''
        self.device.erased = self.now - timedelta(minutes=12)
        self.device.checkin = self.now - timedelta(seconds=10)
        self.device.checkout = self.now
        self.restarting = False
        # self.logger.setLevel(logging.DEBUG)
        self.assertFalse(self.manager.need_to_erase(self.device))

    def test_valid_checkout(self):
        '''test valid device checkout
        '''
        device = self.manager.device(self.device.ecid)
        self.device.erased = self.now - timedelta(hours=3)
        self.device.checkin = self.now - timedelta(hours=2)
        self.device.checkout = self.now - timedelta(hours=1)
        self.device.restarting = False
        # self.logger.setLevel(logging.DEBUG)
        self.assertTrue(self.manager.need_to_erase(self.device))


class TestListRefresh(BaseTestCase):
    '''Complicated tests relying on the replacement of an underlying
    function used by aeios.DeviceManager.list()

    tests verify that the manager caches the results to a file and
    reads the cached results when appropriate as well as refreshes
    the cache when appropriate
    '''
    @classmethod
    def setUpClass(cls):
        super(cls, cls).setUpClass()
        # save original cfgutil.list function for restore after tests
        cls._cfglist = cfgutil.list
    
    @classmethod
    def tearDownClass(cls):
        # restore original cfgutil.list function
        cfgutil.list = cls._cfglist
    
    def setUp(self):
        '''
        '''
        # super(self.__class__, self).setUp()
        BaseTestCase.setUp(self)
        # replacement function to return simple list
        self.listed = []
        for d in self.env[0:2]:
            m = {k:d[k] for k in ['UDID', 'ECID', 'locationID', 
                                  'deviceName', 'deviceType']}
            self.listed.append(m)
        # manually modify the config file with the cached list
        self.manager.config.update({'cfgutilList':self.listed,
                                    'lastListed':self.now})

        # replacement function to return empty list
        def _empty(*args, **kwargs):
            return []
        self.empty = _empty

        # replacement function to return simple device list
        def _simple(*args, **kwargs):
            return self.listed
        self.simple = _simple
        
        # replace cfgutil.list with _simple() above
        cfgutil.list = _simple
        self.listed = self.manager.list()
        # verify function replacement worked
        self.assertEquals(self.listed, _simple())
 
    def tearDown(self):
        # super(self.__class__, self).tearDown()
        BaseTestCase.tearDown(self)

        # remove any cached values
        try:
            self.manager.config.delete('lastListed')
        except:
            pass
        try:
            self.manager.config.delete('cfgutilList')
        except:
            pass

    def test_default_list(self):
        '''test that given default empty values, cached values are 
        populated
        '''
        # delete the values configured in setUp()
        self.manager.config.delete('lastListed')
        self.manager.config.delete('cfgutilList')

        # re-replace cfgutil.list and re-run
        cfgutil.list = self.empty
        self.manager.list()

        # Actual tests
        timestamp = self.manager.config.get('lastListed')
        cached = self.manager.config.get('cfgutilList')
        self.assertIsNotNone(timestamp)
        self.assertIsNotNone(cached)
        
    def test_cached_list_returned(self):
        '''test cached result is returned
        '''
        # re-replace cfgutil.list (should not be called)
        cfgutil.list = self.empty
        listed = self.manager.list()
        # re-run manager.list(), should return cached results
        # (not the replaced function)
        self.assertEquals(listed, self.listed)

    def test_results_cached_to_file(self):
        '''test cached result is written to file
        '''
        listed = self.manager.list()
        file_cache = self.manager.config.get('cfgutilList')
        self.assertItemsEqual(listed, file_cache)

    def test_cached_results_expire(self):
        '''test cached result expires 
        '''
        # manually modify the lastListed to 1 minute ago (force update)
        timestamp = self.now - timedelta(minutes=1)
        self.manager.config.update({'lastListed':timestamp})

        # re-replace cfgutil.list
        cfgutil.list = self.empty
        # verify manager.list() returns results from second replacement
        result = self.manager.list()
        self.assertEquals(result, self.empty())

    def test_forced_refresh(self):
        '''test list can be forcibly refreshed
        '''
        # re-replace cfgutil.list
        cfgutil.list = self.empty
        # verify manager.list() returns results from second replacement
        result = self.manager.list(refresh=True)
        # verify manager.list() refreshes the list
        self.assertEquals(result, self.empty())


@unittest.skip("Not implemented")
class TestRecords(BaseTestCase):
    '''
    Tests for device.Manager.records()
    '''
    def test_all_records(self):
        '''
        test all device records are returned
        '''
        pass

    def test_single_ecid(self):
        '''
        test single device record is returned
        '''
        pass
    
    def test_missing_record(self):
        '''
        test empty list is returned for missing record
        '''
        pass

    def test_specified_ecids(self):
        '''
        test specified device records are returned
        '''
        pass

    def test_non_iterable(self):
        '''
        test error is raised when given a non-iterable
        '''
        pass

    def test_non_ecid(self):
        '''
        test empty list is returned for non-ECID
        '''
        pass


class TestCache(BaseTestCase):
    
    def setUp(self):
        BaseTestCase.setUp(self)
        self.cache = aeios.Cache(self.manager.config)


class TestVerify(BaseTestCase):
    
#     def setUp(self):
#         super(self.__class__, self).setUp()
    
    def test_devices(self):
        pass

class TestThreaded(BaseTestCase):
    pass



if __name__ == '__main__':
    unittest.main(verbosity=2)
