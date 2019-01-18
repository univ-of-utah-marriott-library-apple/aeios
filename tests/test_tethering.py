#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import unittest

'''Tests for ipadmanager.tethering
'''

try:
    import tethering
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    import tethering

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '1.0.0'
__url__ = None
__description__ = 'Tests for ipadmanager.tethering'

LOG = None
DATA = os.path.join(os.path.dirname(__file__), 'data', 'tethering')
OS = None

## 
def setUpModule():
    global LOG, OS
    LOG = logging.getLogger(__name__)
    LOG.addHandler(logging.NullHandler())
    OS = os_version()
    
def tearDownModule():
    pass

## TestCases
class BaseTestCase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.log = LOG
        cls.data = DATA
        cls.version = OS

        is_subclass = cls is not BaseTestCase
        has_setup = cls.setUp is not BaseTestCase.setUp
        if is_subclass and has_setup:
            orig = cls.setUp
            def override(self, *args, **kwargs):
                BaseTestCase.setUp(self)
                return orig(self, *args, **kwargs)
            cls.setUp = override
        
    @classmethod
    def tearDownClass(cls):
        is_subclass = cls is not BaseTestCase
        has_teardown = cls.tearDown is not BaseTestCase.tearDown
        if is_subclass and has_teardown:
            orig = cls.tearDown
            def override(self, *args, **kwargs):
                BaseTestCase.tearDown(self)
                return orig(self, *args, **kwargs)
            cls.tearDown = override
        
    def setUp(self):
        self.log = self.__class__.log
        self.data = self.__class__.data
        self.ver = self.__class__.version
        self.maxDiff = None
        
    def tearDown(self):
        pass


class MockOutputTestCase(BaseTestCase):

    def setUp(self):
        self.assetutil = tethering.assetcachetetheratorutil
        if self.ver.startswith('10.12'):
            self.static_tetherator = tethering._old_tetherator
        else:
            self.static_tetherator = tethering._tetherator
        tethering.assetcachetetheratorutil = self.mockassetutil

    def tearDown(self):
        tethering.assetcachetetheratorutil = self.assetutil

    def mockassetutil(self, log, arg, json=False, _mock=(1,None)):
        '''replaces tethering.assetcachetetheratorutil()
        to mock data that would be returned
        '''
        
        code, name = _mock
        # dummy object to have obj.returncode
        class _dummy(object):
            def __init__(self, c):
                self.returncode = c
        out = None
        if name:
            filename = '{0}.txt'.format(name)
            if self.ver.startswith('10.12'):
                file = os.path.join(self.data, '10.12', filename)
            else:
                file = os.path.join(self.data, filename)
            # instead of running command, read output from file
            with open(file, 'r') as f:
                out = f.read()

        return (_dummy(code), out)
      

class TestSierraParser(MockOutputTestCase):

    def test_empty(self):
        args = [self.log, 'status']
        _, out = self.mockassetutil(*args, _mock=(0,'empty'))
        result = tethering._parse_tetherator_status(self.log, out)
        expected = {}
        self.assertItemsEqual(expected, result)

    def test_disabled(self):
        args = [self.log, 'status']
        _, out = self.mockassetutil(*args, _mock=(0,'disabled'))
        result = tethering._parse_tetherator_status(self.log, out)
        expected = {}
        self.assertItemsEqual(expected, result)

    def test_standard(self):
        args = [self.log, 'status']
        _, out = self.mockassetutil(*args, _mock=(0,'status'))
        result = tethering._parse_tetherator_status(self.log, out)
        expected = [{'Checked In': True, 
                     'Check In Pending': False, 
                     'Device Name': 'test-ipad-pro', 
                     'Tethered': True, 
                     'Device Location ID': 337641472, 
                     'Check In Retry Attempts': 4, 
                     'Serial Number': 'DMPVAA00J28K',
                     'Paired': True}, 
                    {'Checked In': False, 
                     'Check In Pending': False, 
                     'Device Name': 'test-ipad-1', 
                     'Tethered': False, 
                     'Device Location ID': 341835776, 
                     'Check In Retry Attempts': 0, 
                     'Serial Number': 'DMQX7000JF8J',
                     'Paired': False},
                    {'Checked In': False, 
                     'Check In Pending': True, 
                     'Device Name': 'test-ipad-2', 
                     'Tethered': True, 
                     'Device Location ID': 336592896, 
                     'Check In Retry Attempts': 3, 
                     'Serial Number': 'DMPWAA01JF8J',
                     'Paired': True}]
        self.assertItemsEqual(expected, result)


class TestTetherator(MockOutputTestCase):
    
    def test_dynamic_function_mapped(self):
        args = [self.log, 'status']
        dynamic = tethering.tetherator(*args, _mock=(0,'empty'))
        static = self.static_tetherator(*args, _mock=(0,'empty'))
        self.assertEqual(dynamic, static)
    
    def test_standard(self):
        args = [self.log, 'status']
        result = tethering.tetherator(*args, _mock=(0,'status'))
        expected = {'Device Roster': [{'Check In Pending': False,
                     'Check In Attempts': 4, 
                     'Checked In': True, 
                     'Location ID': 337641472, 
                     'Name': 'test-ipad-pro', 
                     'Serial Number': 'DMPVAA00J28K',
                     'Bridged': True,
                     'Paired': True}, 
                    {'Check In Pending': False, 
                     'Check In Attempts': 0, 
                     'Checked In': False, 
                     'Location ID': 341835776, 
                     'Name': 'test-ipad-1', 
                     'Serial Number': 'DMQX7000JF8J',
                     'Bridged': False,
                     'Paired': False},
                    {'Check In Pending': True, 
                     'Check In Attempts': 3, 
                     'Checked In': False, 
                     'Location ID': 336592896, 
                     'Name': 'test-ipad-2', 
                     'Serial Number': 'DMPWAA01JF8J',
                     'Bridged': True,
                     'Paired': True}]}
        self.assertItemsEqual(expected['Device Roster'], 
                                result['Device Roster'])

    def test_disabled(self):
        '''test disabled returns empty device roster
        '''
        args = [self.log, 'status']
        result = tethering.tetherator(*args, _mock=(0,'disabled'))
        expected = {'Device Roster':[]}
        self.assertItemsEqual(expected['Device Roster'], 
                                result['Device Roster'])

    def test_no_devices(self):
        '''test empty devices returns empty roster
        '''
        args = [self.log, 'status']
        result = tethering.tetherator(*args, _mock=(0,'empty'))
        expected = {'Device Roster': []}
        self.assertItemsEqual(expected['Device Roster'], 
                                result['Device Roster'])

    def test_not_enabled(self):
        status = tethering.enabled(self.log, _mock=(1,'disabled'))
        self.assertFalse(status)

    def test_enabled(self):
        status = tethering.enabled(self.log, _mock=(0,'empty'))
        self.assertTrue(status)


class TestDevices(MockOutputTestCase):

    def test_no_devices(self):
        tethering.ENABLED = True
        result = tethering.devices(self.log, _mock=(0,'empty'))
        expected = []
        self.assertEqual(expected, result)

    def test_disabled(self):
        tethering.ENABLED = True
        result = tethering.devices(self.log, _mock=(0,'disabled'))
        expected = []
        self.assertEqual(expected, result)

    def test_standard(self):
        tethering.ENABLED = True
        result = tethering.devices(self.log, _mock=(0,'status'))
        expected = [{'Check In Pending': False,
                     'Check In Attempts': 4, 
                     'Checked In': True, 
                     'Location ID': 337641472, 
                     'Name': 'test-ipad-pro', 
                     'Serial Number': 'DMPVAA00J28K',
                     'Bridged': True,
                     'Paired': True}, 
                    {'Check In Pending': False, 
                     'Check In Attempts': 0, 
                     'Checked In': False, 
                     'Location ID': 341835776, 
                     'Name': 'test-ipad-1', 
                     'Serial Number': 'DMQX7000JF8J',
                     'Bridged': False,
                     'Paired': False},
                    {'Check In Pending': True, 
                     'Check In Attempts': 3, 
                     'Checked In': False, 
                     'Location ID': 336592896, 
                     'Name': 'test-ipad-2', 
                     'Serial Number': 'DMPWAA01JF8J',
                     'Bridged': True,
                     'Paired': True}]
        self.assertItemsEqual(expected, result)

    def test_device_is_tethered(self):
        tethering.ENABLED = True
        sn = 'DMPVAA00J28K'
        m = (0,'status')
        tethered = tethering.device_is_tethered(self.log, sn, _mock=m)
        self.assertTrue(tethered)

    def test_device_is_tethered_disabled(self):
        tethering.ENABLED = False
        sn = 'DMPWAA01JF8J'
        m = (0,'status')
        with self.assertRaises(tethering.Error):
            tethering.device_is_tethered(self.log, sn, _mock=m)

    def test_device_is_not_tethered(self):
        tethering.ENABLED = True
        sn = 'DMPWAA01JF8J'
        m = (0,'status')
        tethered = tethering.device_is_tethered(self.log, sn, _mock=m)
        self.assertFalse(tethered)

    def test_sn_tethered_missing_empty_disabled(self):
        tethering.ENABLED = False
        m = (0,'status')
        with self.assertRaises(tethering.Error):
            tethering.device_is_tethered(self.log, '', _mock=m)

    def test_sn_tethered_missing_empty_enabled(self):
        tethering.ENABLED = True
        m = (0,'status')
        with self.assertRaises(tethering.Error):
            tethering.device_is_tethered(self.log, '', _mock=m)

    def test_devices_are_tethered_single(self):
        tethering.ENABLED = True
        args = (self.log, ['DMPVAA00J28K'])
        m = (0,'status')
        tethered = tethering.devices_are_tethered(*args, _mock=m)
        self.assertTrue(tethered)

    def test_devices_are_not_tethered_single(self):
        tethering.ENABLED = True
        args = (self.log, ['DMPWAA01JF8J'])
        m = (0,'status')
        tethered = tethering.devices_are_tethered(*args, _mock=m)
        self.assertFalse(tethered)

    def test_devices_are_not_tethered_multiple(self):
        tethering.ENABLED = True
        args = (self.log, ['DMPWAA01JF8J', 'DMPVAA00J28K'])
        m = (0,'status')
        tethered = tethering.devices_are_tethered(*args, _mock=m)
        self.assertFalse(tethered)


class TestEnabled(MockOutputTestCase):

    def test_ENABLED_not_none(self):
        self.assertFalse(tethering.ENABLED is None)

    def test_ENABLED_reflects_enabled(self):
        status = tethering.enabled(self.log, _mock=(0,None))
        self.assertTrue(status == tethering.ENABLED)

    def test_updated_by_default(self):
        reverse_status = not tethering.enabled(self.log)
        tethering.ENABLED = reverse_status
        status = tethering.enabled(self.log)
        self.assertTrue(status == tethering.ENABLED)

    def test_updated_with_refresh(self):
        reverse_status = not tethering.enabled(self.log)
        tethering.ENABLED = reverse_status
        status = tethering.enabled(self.log, refresh=True)
        self.assertTrue(status == tethering.ENABLED)

    def test_not_updated_without_refresh(self):
        reverse_status = not tethering.enabled(self.log)
        tethering.ENABLED = reverse_status
        status = tethering.enabled(self.log, refresh=False)
        self.assertTrue(status == tethering.ENABLED)
        self.assertTrue(status == reverse_status)


class ActionTests(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        BaseTestCase.setUpClass()
        tethering.stop(cls.log)

    @classmethod
    def tearDownClass(cls):
        BaseTestCase.tearDownClass()
        tethering.stop(cls.log)

    def test_start_not_running(self):
        if not tethering.enabled(self.log):
            tethering.start(self.log)
        else:
            raise Exception("test wasn't run in proper order")
        self.assertTrue(tethering.enabled(self.log))

    def test_start_running(self):
        if tethering.enabled(self.log):
            tethering.start(self.log)
        else:
            raise Exception("test wasn't run in proper order")
        enabled = tethering.enabled(self.log)
        self.assertTrue(enabled)

    def test_stop_not_running(self):
        if not tethering.enabled(self.log):
            tethering.stop(self.log)
        else:
            raise Exception("test wasn't run in proper order")
        enabled = tethering.enabled(self.log)
        self.assertFalse(enabled)

    def test_stop_running(self):
        if tethering.enabled(self.log):
            tethering.stop(self.log)
        else:
            raise Exception("test wasn't run in proper order")
        enabled = tethering.enabled(self.log)
        self.assertFalse(enabled)
    
    def test_restart_not_running(self):
        if not tethering.enabled(self.log):
            tethering.restart(self.log)
        else:
            raise Exception("test wasn't run in proper order")
        self.assertTrue(tethering.enabled(self.log))

    def test_restart_running(self):
        if tethering.enabled(self.log):
            tethering.restart(self.log)
        else:
            raise Exception("test wasn't run in proper order")
        enabled = tethering.enabled(self.log)
        self.assertTrue(enabled)


class TestUnsupported(BaseTestCase):
    
    def test_restart(self):
        '''verify tethering.Error is raised on restart
        '''
        with self.assertRaises(tethering.Error):
            tethering.restart(self.log)

    def test_stop(self):
        '''verify tethering.Error is raised on stop
        '''
        with self.assertRaises(tethering.Error):
            tethering.stop(self.log)

    def test_start(self):
        '''verify tethering.Error is raised on start
        '''
        with self.assertRaises(tethering.Error):
            tethering.start(self.log)

    def test_tethered_caching(self):
        '''verify tethering.Error is raised on tethered_caching
        '''
        with self.assertRaises(tethering.Error):
            tethering.tethered_caching(self.log, '-b')


class TestTetheringStatus(BaseTestCase):

    def test_enabled_refreshes_state(self):
        pass

## Extra
def os_version():
    cmd = ['/usr/sbin/system_profiler', 'SPSoftwareDataType', '-xml']
    out = subprocess.check_output(cmd)
    info = plistlib.readPlistFromString(out)[0]
    os_ver = info['_items'][0]['os_version'] # 'macOS 10.12.6 (16G1510)'
    return os_ver.split(" ")[1]              # '10.12.6'

## Test Loading
def genericTests(loader):
    testcases = [
            TestTetherator, 
            TestDevices,
            TestEnabled
        ]
    suites = []
    for cls in testcases:
        suites.append(loader.loadTestsFromTestCase(cls))        
    return unittest.TestSuite(suites)

def sierraTests(loader):
    testcases = [
            TestSierraParser
        ]
    suites = []
    for cls in testcases:
        suites.append(loader.loadTestsFromTestCase(cls))        
    return unittest.TestSuite(suites)

def nonSierraTests(loader):
    testcases = [
            TestUnsupported, 
        ]
    suites = []
    for cls in testcases:
        suites.append(loader.loadTestsFromTestCase(cls))        
    return unittest.TestSuite(suites)

def extended_tests(loader):
    tests = [
        # stopped
        'test_stop_not_running', 
        'test_start_not_running', 
        #running
        'test_restart_running', 
        'test_start_running', 
        'test_stop_running', 
        #stopped
        'test_restart_not_running']
    return unittest.TestSuite(map(ActionTests, tests))
    

if __name__ == '__main__':
    import subprocess
    import plistlib

    loader = unittest.TestLoader()
    generic = genericTests(loader)
    if os_version().startswith('10.12'):
        dynamic = sierraTests(loader)
    else:
        dynamic = nonSierraTests(loader)
    
    suites = unittest.TestSuite([generic, dynamic])
    if '--extended' in sys.argv:
        _extended = extended_tests(loader)
        suites = unittest.TestSuite([generic, dynamic, _extended])
    
    unittest.TextTestRunner(verbosity=2).run(suites)
