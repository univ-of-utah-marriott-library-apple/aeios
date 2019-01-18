#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import unittest 

'''Tests for ipadmanager.devicemanager
'''

from devicemanager import DeviceManager

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
    shutil.rmtree(TMPDIR)


class BaseTestCase(unittest.TestCase):
    
    file = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = TMPDIR
        cls.env = [{'ECID': '0x123456789ABCD0',
                    'UDID': 'a0111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'checkout-ipad-1',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000001'},
                   {'ECID': '0x123456789ABCD1',
                    'UDID': 'a1111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'checkout-ipad-2',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000002'},
                   {'ECID': '0x123456789ABCD2',
                    'UDID': 'a2111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'checkout-ipad-3',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000003'},
                   {'ECID': '0x123456789ABCD3',
                    'UDID': 'a3111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'checkout-ipad-4',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000004'},
                   {'ECID': '0x123456789ABCD4',
                    'UDID': 'a4111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'checkout-ipad-5',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000005'},
                   {'ECID': '0x123456789ABCD5',
                    'UDID': 'a5111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'checkout-ipad-6',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000006'},
                   {'ECID': '0x123456789ABCD6',
                    'UDID': 'a6111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'checkout-ipad-7',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000007'},
                   {'ECID': '0x123456789ABCD7',
                    'UDID': 'a7111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'checkout-ipad-8',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000008'},
                   {'ECID': '0x123456789ABCD8',
                    'UDID': 'a8111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'checkout-ipad-9',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000009'},
                   {'ECID': '0x123456789ABCD9',
                    'UDID': 'a9111222333444555666777888999abcdefabcde',
                    'bootedState': 'Booted',
                    'buildVersion': '15G77',
                    'deviceName': 'checkout-ipad-10',
                    'deviceType': 'iPad7,5',
                    'firmwareVersion': '11.4.1',
                    'locationID': '0x00000010'}]
        
    @classmethod
    def tearDownClass(cls):
        os.remove(cls.file)
        
    def setUp(self):
        id = 'edu.utah.mlib.test'
        self.path = self.__class__.tmp 
        self.manager = DeviceManager(id, path=self.path)
        self.env = self.__class__.env
        self.__class__.file = self.manager.file
    
    def tearDown(self):
        pass


class TestThreaded(BaseTestCase):
    pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
