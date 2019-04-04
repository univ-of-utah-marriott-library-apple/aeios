# -*- coding: utf-8 -*-

import os
import json
import shutil
import logging
import unittest 
import datetime as dt

from actools import cfgutil

"""
Tests for actools.cfgutil
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright(c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = '1.0.0'

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

LOCATION = os.path.dirname(__file__)
DATA = os.path.join(LOCATION, 'data', 'cfgutil')
TMPDIR = os.path.join(LOCATION, 'tmp', 'cfgutil')


class BaseTestCase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        pass
            
    @classmethod
    def tearDownClass(cls):
        pass
        
    def setUp(self):
        self.data = DATA
        self.tmp = TMPDIR
                
    def tearDown(self):
        pass


class MockOutputTestCase(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        self.mockfiles = os.path.join(self.data, 'mock')
    
    @staticmethod
    def lines(file):
        with open(file) as f:
            for line in f:
                yield line

    def mock(self, path, default=None):
        line = self.lines(path)

        def _mock():
            try:
                _line = next(line)
                return json.loads(_line)
            except StopIteration:
                if default:
                    return default

        return _mock


class ResultErrorTests(BaseTestCase):

    def test_empty_result(self):
        """
        test cfgutil.Error is raised without params
        """
        with self.assertRaises(TypeError):
            cfgutil.Result()


class ResultTestCase(BaseTestCase):
    """
    Base TestCase for cfgutil.Result
    """

    def setUp(self):
        BaseTestCase.setUp(self)
        self.result = None

    def test_output_defined(self):
        """
        test result.output is defined
        """
        if self.result:
            self.assertIsNotNone(self.result.output)
    
    def test_output_type(self):
        """
        test result.output is dict
        """
        if self.result:
            self.assertIsInstance(self.result.output, dict)

    # def test_errors_defined(self):
    #     """
    #     test result.error defined
    #     """
    #     if self.result:
    #         self.assertIsNotNone(self.result.errors)
    # 
    # def test_errors_type(self):
    #     """
    #     test result.error is dict
    #     """
    #     if self.result:
    #         self.assertIsInstance(self.result.output, dict)

    def test_missing_defined(self):
        """
        test result.missing defined
        """
        if self.result:
            self.assertIsNotNone(self.result.missing)
    
    def test_missing_type(self):
        """
        test result.missing is list
        """
        if self.result:
            self.assertIsInstance(self.result.missing, list)

    def test_ecids_defined(self):
        """
        test result.ecids defined
        """
        if self.result:
            self.assertIsNotNone(self.result.ecids)
    
    def test_ecids_type(self):
        """
        test result.ecids is list
        """
        if self.result:
            self.assertIsInstance(self.result.ecids, list)


class MinimalResultsTest(ResultTestCase):
    
    def setUp(self):
        ResultTestCase.setUp(self)
        self.cfgout = {'Output': {}, 'Devices': [], 'Command': 'test'}
        self.result = cfgutil.Result(self.cfgout)

    def test_nothing_missing(self):
        self.assertEquals(self.result.missing, [])

    def test_get_ecid(self):
        self.assertIsNone(self.result.get('0x000000001'))


class EmptyResult(ResultTestCase):
    """
    Tests for minimal Result
    """
    def setUp(self):
        self.result = cfgutil.Result({})

    def test_nothing_missing(self):
        self.assertEquals(self.result.missing, [])

    def test_get_ecid(self):
        self.assertIsNone(self.result.get('0x000000001'))


if __name__ == '__main__':
    unittest.main(verbosity=1)
