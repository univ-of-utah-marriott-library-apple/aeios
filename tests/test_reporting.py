# -*- coding: utf-8 -*-

import os
# import shutil
import logging
import unittest 

from aeios import reporting 

"""
Tests for aeios.reporting
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "0.0.0"

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

LOCATION = os.path.dirname(__file__)
DATA = os.path.join(LOCATION, 'data', 'reporting')
TMPDIR = os.path.join(LOCATION, 'tmp', 'reporting')


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


class ReportingTestCase(BaseTestCase):
    
    def setUp(self):
        BaseTestCase.setUp(self)


if __name__ == '__main__':
    fmt = ('%(asctime)s %(process)d: %(levelname)6s: '
           '%(name)s - %(funcName)s(): %(message)s')
    # logging.basicConfig(format=fmt, level=logging.DEBUG)
    unittest.main(verbosity=1)
