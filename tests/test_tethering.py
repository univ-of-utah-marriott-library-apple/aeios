# -*- coding: utf-8 -*-

import os
import sys
import logging
import unittest
import plistlib
import subprocess

from aeios import tethering

"""
Tests for aeios.tethering
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "2.0.0"

OS = None
ACTIONABLE = None
LOCATION = os.path.dirname(__file__)
DATA = os.path.join(LOCATION, 'data', 'tethering')

def setUpModule():
    global OS, ACTIONABLE
    OS = os_version()
    try:
        tethering.stop()
        ACTIONABLE = True
    except tethering.Error:
        # if we can't stop tethering, we can't run ActionTests
        ACTIONABLE = False


def tearDownModule():
    pass


# TestCases
class BaseTestCase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.data = DATA
        cls.version = OS
        
    @classmethod
    def tearDownClass(cls):
        pass
        
    def setUp(self):
        self.data = self.__class__.data
        self.ver = self.__class__.version
        self.maxDiff = None
        
    def tearDown(self):
        pass


class MockOutputTestCase(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        self.assetutil = tethering.assetcachetetheratorutil
        if self.ver.startswith('10.12'):
            self.static_tetherator = tethering._old_tetherator
        else:
            self.static_tetherator = tethering._tetherator
        tethering.assetcachetetheratorutil = self.mockassetutil

    def tearDown(self):
        BaseTestCase.tearDown(self)
        tethering.assetcachetetheratorutil = self.assetutil

    def lines(self, file):
        with open(file) as f:
            for line in f:
                yield line

    def mock(self, file, default=None):
        line = self.lines(file)

        def _mock():
            try:
                _line = next(line)
            except StopIteration:
                return {'activity': None, 'alerts': [], 'busy': False}
            try:
                return json.loads(_line)
            except ValueError:
                if default:
                    return default

        return _mock

    def mockassetutil(self, arg, json=False, _mock=(1, None)):
        """
        replaces tethering.assetcachetetheratorutil() to mock data that 
        would be returned
        """
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

    def setUp(self):
        self.ver = '10.12'
        MockOutputTestCase.setUp(self)

    def test_empty(self):
        _, out = self.mockassetutil('status', _mock=(0, 'empty'))
        result = tethering._parse_tetherator_status(out)
        expected = {}
        self.assertItemsEqual(expected, result)

    def test_disabled(self):
        _, out = self.mockassetutil('status', _mock=(0, 'disabled'))
        result = tethering._parse_tetherator_status(out)
        expected = {}
        self.assertItemsEqual(expected, result)

    def test_standard(self):
        _, out = self.mockassetutil('status', _mock=(0, 'status'))
        result = tethering._parse_tetherator_status(out)
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
    
    def setUp(self):
        self.ver = '10.13'
        MockOutputTestCase.setUp(self)
    
    def test_dynamic_function_mapped(self):
        args = ['status']
        dynamic = tethering.tetherator(*args, _mock=(0, 'empty'))
        static = self.static_tetherator(*args, _mock=(0, 'empty'))
        self.assertEqual(dynamic, static)
    
    def test_standard(self):
        args = ['status']
        result = tethering.tetherator(*args, _mock=(0, 'status'))
        expected = {'Device Roster': [
                        {'Check In Pending': False,
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
        """test disabled returns empty device roster
        """
        args = ['status']
        result = tethering.tetherator(*args, _mock=(0, 'disabled'))
        expected = {'Device Roster':[]}
        self.assertItemsEqual(expected['Device Roster'], 
                                result['Device Roster'])

    def test_no_devices(self):
        """test empty devices returns empty roster
        """
        args = ['status']
        result = tethering.tetherator(*args, _mock=(0, 'empty'))
        expected = {'Device Roster': []}
        self.assertItemsEqual(expected['Device Roster'], 
                                result['Device Roster'])

    def test_not_enabled(self):
        status = tethering.enabled(_mock=(1, 'disabled'))
        self.assertFalse(status)

    def test_enabled(self):
        status = tethering.enabled(_mock=(0, 'empty'))
        self.assertTrue(status)


class TestDevices(MockOutputTestCase):

    def test_no_devices(self):
        tethering.ENABLED = True
        result = tethering.devices(_mock=(0, 'empty'))
        expected = []
        self.assertEqual(expected, result)

    def test_disabled(self):
        tethering.ENABLED = True
        result = tethering.devices(_mock=(0, 'disabled'))
        expected = []
        self.assertEqual(expected, result)

    def test_standard(self):
        tethering.ENABLED = True
        result = tethering.devices(_mock=(0, 'status'))
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
        m = (0, 'status')
        tethered = tethering.device_is_tethered('DMPVAA00J28K', _mock=m)
        self.assertTrue(tethered)

    def test_device_is_tethered_disabled(self):
        tethering.ENABLED = False
        m = (0, 'status')
        with self.assertRaises(tethering.Error):
            tethering.device_is_tethered('DMPWAA01JF8J', _mock=m)

    def test_device_is_not_tethered(self):
        tethering.ENABLED = True
        m = (0, 'status')
        tethered = tethering.device_is_tethered('DMPWAA01JF8J', _mock=m)
        self.assertFalse(tethered)

    def test_sn_tethered_missing_empty_disabled(self):
        tethering.ENABLED = False
        m = (0, 'status')
        with self.assertRaises(tethering.Error):
            tethering.device_is_tethered('', _mock=m)

    def test_sn_tethered_missing_empty_enabled(self):
        tethering.ENABLED = True
        m = (0, 'status')
        with self.assertRaises(tethering.Error):
            tethering.device_is_tethered('', _mock=m)

    def test_devices_are_tethered_single(self):
        tethering.ENABLED = True
        m = (0, 'status')
        tethered = tethering.devices_are_tethered(['DMPVAA00J28K'], _mock=m)
        self.assertTrue(tethered)

    def test_devices_are_not_tethered_single(self):
        tethering.ENABLED = True
        m = (0, 'status')
        tethered = tethering.devices_are_tethered(['DMPWAA01JF8J'], _mock=m)
        self.assertFalse(tethered)

    def test_devices_are_not_tethered_multiple(self):
        tethering.ENABLED = True
        sns = ['DMPWAA01JF8J', 'DMPVAA00J28K']
        m = (0, 'status')
        tethered = tethering.devices_are_tethered(sns, _mock=m)
        self.assertFalse(tethered)


class TestEnabled(MockOutputTestCase):

    def test_ENABLED_not_none(self):
        self.assertFalse(tethering.ENABLED is None)

    def test_ENABLED_reflects_enabled(self):
        status = tethering.enabled(_mock=(0, None))
        self.assertTrue(status == tethering.ENABLED)

    def test_updated_by_default(self):
        reverse_status = not tethering.enabled()
        tethering.ENABLED = reverse_status
        status = tethering.enabled()
        self.assertTrue(status == tethering.ENABLED)

    def test_updated_with_refresh(self):
        reverse_status = not tethering.enabled()
        tethering.ENABLED = reverse_status
        status = tethering.enabled(refresh=True)
        self.assertTrue(status == tethering.ENABLED)

    def test_not_updated_without_refresh(self):
        reverse_status = not tethering.enabled()
        tethering.ENABLED = reverse_status
        status = tethering.enabled(refresh=False)
        self.assertTrue(status == tethering.ENABLED)
        self.assertTrue(status == reverse_status)


@unittest.skipUnless(ACTIONABLE, "unable to test tethering actions")
class ActionTests(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        BaseTestCase.setUpClass()
        tethering.stop()

    @classmethod
    def tearDownClass(cls):
        BaseTestCase.tearDownClass()
        tethering.stop()

    def test_start_not_running(self):
        if not tethering.enabled():
            tethering.start()
        else:
            raise Exception("test wasn't run in proper order")
        self.assertTrue(tethering.enabled())

    def test_start_running(self):
        if tethering.enabled():
            tethering.start()
        else:
            raise Exception("test wasn't run in proper order")
        enabled = tethering.enabled()
        self.assertTrue(enabled)

    def test_stop_not_running(self):
        if not tethering.enabled():
            tethering.stop()
        else:
            raise Exception("test wasn't run in proper order")
        enabled = tethering.enabled()
        self.assertFalse(enabled)

    def test_stop_running(self):
        if tethering.enabled():
            tethering.stop()
        else:
            raise Exception("test wasn't run in proper order")
        enabled = tethering.enabled()
        self.assertFalse(enabled)
    
    def test_restart_not_running(self):
        if not tethering.enabled():
            tethering.restart()
        else:
            raise Exception("test wasn't run in proper order")
        self.assertTrue(tethering.enabled())

    def test_restart_running(self):
        if tethering.enabled():
            tethering.restart()
        else:
            raise Exception("test wasn't run in proper order")
        enabled = tethering.enabled()
        self.assertTrue(enabled)


class TestUnsupported(BaseTestCase):
    
    def test_restart(self):
        """
        verify tethering.Error is raised on restart
        """
        with self.assertRaises(tethering.Error):
            tethering.restart()

    def test_stop(self):
        """
        verify tethering.Error is raised on stop
        """
        with self.assertRaises(tethering.Error):
            tethering.stop()

    def test_start(self):
        """
        verify tethering.Error is raised on start
        """
        with self.assertRaises(tethering.Error):
            tethering.start()

    def test_tethered_caching(self):
        """
        verify tethering.Error is raised on tethered_caching
        """
        with self.assertRaises(tethering.Error):
            tethering.tethered_caching('-b')


@unittest.skip("Unfinished")
class TestTetheringStatus(BaseTestCase):
    """
    test_enabled_refreshes_state()
    """
    pass


# Extra
def os_version():
    cmd = ['/usr/sbin/system_profiler', 'SPSoftwareDataType', '-xml']
    out = subprocess.check_output(cmd)
    info = plistlib.readPlistFromString(out)[0]
    os_ver = info['_items'][0]['os_version'] # 'macOS 10.12.6 (16G1510)'
    return os_ver.split(" ")[1]              # '10.12.6'


# Test Loading
def genericTests(loader):
    testcases = [TestTetherator, TestDevices, TestEnabled]
    suites = []
    for cls in testcases:
        suites.append(loader.loadTestsFromTestCase(cls))        
    return unittest.TestSuite(suites)


def sierraTests(loader):
    testcases = [TestSierraParser]
    suites = []
    for cls in testcases:
        suites.append(loader.loadTestsFromTestCase(cls))        
    return unittest.TestSuite(suites)


def nonSierraTests(loader):
    testcases = [TestUnsupported]
    suites = []
    for cls in testcases:
        suites.append(loader.loadTestsFromTestCase(cls))        
    return unittest.TestSuite(suites)


def extended_tests(loader):
    tests = [# stopped
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

    unittest.TextTestRunner(verbosity=1).run(suites)
