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

try:
    import cfgutil
except ImportError:
    from actools import cfgutil

LOGDIR = os.path.join(os.path.dirname(__file__), 'private')
LOG = os.path.join(LOGDIR, 'cfgutilexec.log')

def setUpModule():
    # cfgutil.TESTING = True
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

class TestExecutionRecord(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.kwargs = {'file': LOG}
        #.ecids = [x['ECID'] for x in cfgutil.list(**cls.kwargs)]
        cls.ecids = ['0x1D78A614D80026', '0x1D481C2E300026', 
                     '0x10000000000001']
    
    def setUp(self):
        self.kwargs = self.__class__.kwargs
        self.ecids = self.__class__.ecids

#     def testRead(self):
#         import ast
#         data = []
#         with open(LOG, 'r') as f:
#             for line in f.readlines():
#                 data.append(ast.literal_eval(line))
#         print(data)

    def test_run_prepare(self):
        cfgutil.prepareDEP(self.ecids, **self.kwargs)

#     def test_run_erase(self):
#         cfgutil.erase(self.ecids, **self.kwargs)


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
            with self.assertRaises(ValueError):
                self.action([])

    def test_missing_device(self):
        '''test CfgutilError is raised when called on missing ECID
        '''
        if self.action:
            with self.assertRaises(cfgutil.CfgutilError):
                ecids = [self.missing]
                devices = self.action(ecids, *self.args, **self.kwargs)


@unittest.skip("not implemented")
class TestCfgutilError(BaseTestCase):
    '''Test for CfgutilError
    '''
    pass


@unittest.skip("not implemented")
class TestResult(BaseTestCase):
    pass


@unittest.skip("takes too long")
class TestErase(ActionTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.action = cfgutil.erase
        self.ecids = [] #need to come up with a way of finding these


#     @unittest.skipIf(MISSINGBIN, "cfgutil binary missing")
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


@unittest.skip("takes too long")
class TestPrepareDEP(ActionTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.action = cfgutil.prepareDEP


@unittest.skip("takes too long")
class TestWallpaper(BaseTestCase):
    pass


@unittest.skip("takes too long")
class TestPrepareManually(ActionTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.action = cfgutil.prepareManually


@unittest.skip("takes too long")
class TestGet(BaseTestCase):
    pass


@unittest.skip("takes too long")
class TestList(BaseTestCase):
    pass


@unittest.skip("takes too long")
class TestRequiresAuth(BaseTestCase):
    pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
