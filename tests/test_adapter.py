#!/usr/bin/python
# -*- coding: utf-8 -*-

# import os
# import shutil
import unittest 

'''Tests for actools.adapter
'''

from actools import adapter

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '1.0.0'
__url__ = None
__description__ = 'Tests for actools.adapter'

## location for temporary files created with tests
# TMPDIR = os.path.join(os.path.dirname(__file__), 'tmp')

def setUpModule():
    pass
    
def tearDownModule():
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


class TestInstallVPPApps(BaseTestCase):
    pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
