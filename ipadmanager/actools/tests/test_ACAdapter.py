#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
# import shutil
import unittest 
from adapter import ACADAPTER

'''Tests for ACAdapter.scpt
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '1.0.0'
__url__ = None
__description__ = 'Tests for ACAdapter.scpt'


def setUpModule():
    pass

def tearDownModule():
    # shutil.rmtree(TMPDIR)
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


class TestACAdapterLaunch(BaseTestCase):
    pass


class TestConvertJSONToAS(BaseTestCase):
    pass


class TestBuildRecord(BaseTestCase):
    pass


class TestGetRecordValue(BaseTestCase):
    pass


class TestMaximize(BaseTestCase):
    pass


class TestPutWindowIntoListViewMode(BaseTestCase):
    pass


class TestAllWindows(BaseTestCase):
    pass


class TestDeviceWindow(BaseTestCase):
    pass


class TestParseUI(BaseTestCase):
    pass


class TestGetDeviceInfo(BaseTestCase):
    pass


class TestGetTableInfo(BaseTestCase):
    pass


class TestSelectDevices(BaseTestCase):
    pass


class TestSelectApps(BaseTestCase):
    pass


class TestSelectFromTable(BaseTestCase):
    pass


class TestFindTargetPrompt(BaseTestCase):
    pass


class TestStatus(BaseTestCase):
    pass


class TestInstallVPPApps(BaseTestCase):
    pass


class TestApplyBlueprint(BaseTestCase):
    pass


class TestPerformAction(BaseTestCase):
    pass


class TestListDevices(BaseTestCase):
    pass


if __name__ == '__main__':
    unittest.main(verbosity=1)
