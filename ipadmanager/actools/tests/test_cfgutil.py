#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import subprocess
import unittest

'''Tests for actools.cfgutil
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '1.0.1'
__url__ = None
__description__ = 'Tests for actools.cfgutil'

from actools import cfgutil

cmd = ['/usr/bin/cfgutil', 'version']
try:
    VERSION = subprocess.check_output(cmd).rstrip()
except OSError as e:
    if e.errno == 2:
        print("WARNING: missing cfgutil: some tests will not be run...", 
              file=sys.stderr)
        MISSINGBIN = True
    else:
        raise e


def setUpModule():
    pass

def tearDownModule():
    '''One time cleanup for entire module.
    '''
    # OPTIONAL
    pass


class BaseTestCase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass
        
    def setUp(self):
        pass
        
    def tearDown(self):
        pass


class ActionTestCase(BaseTestCase):
    '''Test common behavior across all actions
    '''
    def setUp(self):
        self.action = None
        self.missing = '0x00000000000001'
        self.args = ()
        self.kwargs = {}

    def test_empty(self):
        '''test TypeError is raised when called without params
        '''
        if self.action:
            with self.assertRaises(TypeError):
                self.action()

    def test_empty_list(self):
        '''test CfgutilError is raised when called with empty list
        '''
        if self.action:
            with self.assertRaises(cfgutil.CfgutilError):
                self.action([])

    @unittest.skipIf(MISSINGBIN, "cfgutil binary missing")
    def test_missing_device(self):
        '''test CfgutilError is raised when called on missing ECID
        '''
        if self.action:
            with self.assertRaises(cfgutil.CfgutilError):
                ecids = [self.missing]
                devices = self.action(ecids, *self.args, **self.kwargs)


class TestCfgutilError(BaseTestCase):
    '''Test for CfgutilError
    '''
    pass


class TestErase(ActionTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.action = cfgutil.erase
        self.ecids = [] #need to come up with a way of finding these


    @unittest.skipIf(MISSINGBIN, "cfgutil binary missing")
    def test_erase_devices_with_missing_device(self):
        '''test what happens when missing device is included
        '''
        try:
            devices = cfgutil.erase(self.ecids + self.missing)
            self.fail('did not raise cfgutil.CfgutilError')            
        except cfgutil.CfgutilError as e:
            self.assertTrue(e.missing)
            self.assertTrue(e.succeeded)
            self.assertIn(self.missing[0], e.missing)
            self.assertItemsEqual(self.ecids, e.succeeded)
        except Exception as e:
            ecls = e.__class__
            self.fail("incorrect Exception raised: {0}".format(ecls))


class TestPrepareDEP(ActionTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.action = cfgutil.prepareDEP


class TestWallpaper(BaseTestCase):
    pass


class TestPrepareManually(ActionTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.action = cfgutil.prepareManually


class TestInstalledApps(ActionTestCase):
    pass


class TestGet(BaseTestCase):
    pass


class TestList(BaseTestCase):
    pass


class TestRequiresAuth(BaseTestCase):
    pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
