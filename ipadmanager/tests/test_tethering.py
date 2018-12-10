#!/usr/bin/python
# -*- coding: utf-8 -*-

# import os
# import shutil
# import plistlib
# import time
# from datetime import datetime

import logging
import unittest
import sys
import subprocess
import plistlib

'''Tests for ipadmanager.tethering
'''

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
parentdir = os.path.dirname(dir)
sys.path.append(parentdir)
import tethering

print(tethering.__file__)
help(tethering)


__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '1.0.0'
__url__ = None
__description__ = 'Tests for ipadmanager.tethering'

## location for temporary files created with tests
# TMPDIR = os.path.join(os.path.dirname(__file__), 'tmp')

raise SystemExit()

LOG = None
DATA = os.path.join(os.path.dirname(__file__), 'data', 'tethering')

def setUpModule():
    global LOG
    LOG = logging.getLogger(__name__)
    LOG.addHandler(logging.NullHandler())
    

def tearDownModule():
    pass


class BaseTestCase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.log = LOG
        cls.data = DATA
        
    @classmethod
    def tearDownClass(cls):
        pass
        
    def setUp(self):
        self.log = self.__class__.log
        self.data = self.__class__.data
        
    def tearDown(self):
        pass
    
    def mockAssetCacheTetheratorUtil(self, name):
        '''mock output from commands
        '''
        file = os.path.join(self.data, name)        
        with open(file, 'r') as f:
            return f.read()


class TestSierraParser(BaseTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.data = os.path.join(self.data, 'parser')

    def test_empty(self):
        pass

    def test_standard(self):
        pass

    def test_simple(self):
        pass

    def test_complex(self):
        pass


class TestTetheratorSierra(BaseTestCase):

    def test_not_enabled(self):
        pass

    def test_no_devices(self):
        pass

    def test_devices(self):
        pass


class TestTetherator(BaseTestCase):
    
    def test_not_enabled(self):
        pass

    def test_no_devices(self):
        pass

    def test_devices(self):
        pass


class TestDevices(BaseTestCase):
    pass


class TestEnabled(BaseTestCase):
    
    def test_not_enabled(self):
        self.assertFalse(tethering.enabled())

    def test_ENABLED_not_none(self):
        self.assertFalse(tethering.ENABLED is None)


class TestStartSierra(BaseTestCase):
    
    def test_start_running(self):
        raise NotImplementedError()

    def test_start_not_running(self):
        raise NotImplementedError()


class TestStart(BaseTestCase):

    def test_start(self):
        '''verify tethering.Error is raised
        '''
        with self.assertRaises(tethering.Error):
            tethering.start(self.log)


class TestStopSierra(BaseTestCase):
    
    def test_stop_running(self):
        raise NotImplementedError()

    def test_stop_not_running(self):
        raise NotImplementedError()


class TestStop(BaseTestCase):

    def test_stop_running(self):
        '''verify tethering.Error is raised
        '''
        with self.assertRaises(tethering.Error):
            tethering.stop(self.log)

    def test_stop_not_running(self):
        with self.assertRaises(tethering.Error):
            tethering.stop(self.log)


class TestRestartSierra(BaseTestCase):
    
    def test_restart(self):
        raise NotImplementedError()


class TestRestart(BaseTestCase):
    
    def test_restart_stopped(self):
        '''verify tethering.Error is raised
        '''
        with self.assertRaises(tethering.Error):
            tethering.restart(self.log)

    def test_restart_running(self):
        '''verify tethering.Error is raised
        '''
        with self.assertRaises(tethering.Error):
            tethering.restart(self.log)

class TestTetheringStatus(BaseTestCase):
    pass


def os_version():
    cmd = ['/usr/sbin/system_profiler', 'SPSoftwareDataType', '-xml']
    out = subprocess.check_output(cmd)
    info = plistlib.readPlistFromString(out)[0]
    os_ver = info['_items'][0]['os_version'] # 'macOS 10.12.6 (16G1510)'
    return os_ver.split(" ")[1]              # '10.12.6'

def genericTests(loader):
    loader = unittest.TestLoader()
    suites = []
    return unittest.TestSuite(suites)

def sierraTests2(loader):
    cases = [TestStartSierra, 
             TestStopSierra, 
             TestRestartSierra, 
             TestTetheratorSierra]
    suites = []
    for cls in cases:
        suites.append(loader.loadTestsFromTestCase(cls))        
    return unittest.TestSuite(suites)


def sierraTests(loader):
    start = loader.loadTestsFromTestCase(TestStartSierra)
    stop = loader.loadTestsFromTestCase(TestStopSierra)
    restart = loader.loadTestsFromTestCase(TestRestartSierra)
    tether = loader.loadTestsFromTestCase(TestTetheratorSierra)
    return unittest.TestSuite([start, stop, restart, tether])

def nonSierraTests(loader):
    start = loader.loadTestsFromTestCase(TestStart)
    stop = loader.loadTestsFromTestCase(TestStop)
    restart = loader.loadTestsFromTestCase(TestRestart)
    tether = loader.loadTestsFromTestCase(TestTetherator)
    return unittest.TestSuite([start, stop, restart, tether])


if __name__ == '__main__':
    # need to figure out how to load test suites on specific OS's
    # unittest.main(verbosity=2)
    import subprocess
    import plistlib
    loader = unittest.TestLoader()
    generic = genericTests(loader)
    if os_version().startswith('10.12'):
        dynamic = sierraTests2(loader)
    else:
        dynamic = nonSierraTests(loader)
    
    suites = unittest.TestSuite([generic, dynamic])
    
    unittest.TextTestRunner(verbosity=2).run(suites)
