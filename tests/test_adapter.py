#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import unittest 
import json
import logging

from actools import adapter

'''
Tests for actools.adapter
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = ('Copyright (c) 2019'
                 ' University of Utah, Marriott Library')
__license__ = "MIT"
__version__ = '1.0.0'
__url__ = None
__description__ = 'Tests for actools.adapter'


logging.getLogger(__name__).addHandler(logging.NullHandler())

LOCATION = os.path.dirname(__file__)
DATA = os.path.join(LOCATION, 'data', 'adapter')
TMPDIR = os.path.join(LOCATION, 'tmp', 'adapter')


def setUpModule():
    '''
    create tmp directory
    '''
    try:
        os.mkdir(TMPDIR)
    except OSError as e:
        if e.errno != 17:
            # raise Exception unless TMP already exists
            raise
    
def tearDownModule():
    '''
    remove tmp directory
    '''
    shutil.rmtree(TMPDIR)


## TestCases
class BaseTestCase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.data = DATA

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
        self.data = self.__class__.data
        
    def tearDown(self):
        pass


class MockOutputTestCase(BaseTestCase):

    def setUp(self):
        self.adapter = adapter.acadapter
        adapter.acadapter = self.adapter

    def tearDown(self):
        adapter.acadapter = self.adapter

    def mockadapter(self, command, data=None, _mock=(1,None)):
        '''
        replaces adapter.acadapter() to mock data that would be returned
        '''
        
        code, name = _mock
        # mock subprocess.Popen object to have return code
        class _dummy(object):
            def __init__(self, c):
                self.returncode = c

        out = None
        if name:
            file = os.path.join(self.data, filename)
            # instead of running command, read output from file
            with open(file, 'r') as f:
                out = f.read()

        return (_dummy(code), out)


# class TestStatus(BaseTestCase):
# 
#     def setUp(self):
#         _status = '{"activity":{"options":[],"info":["Step 1 of 27: Assigning a license for “Autodesk ReCap Pro for mobile”","Adding apps on “student-checkout-ipad-10”"],"choices":["Cancel"]},"alerts":[{"options":["Apply to all apps"],"info":["An unexpected error has occurred with “student-checkout-ipad-10”.","Internal error [ConfigurationUtilityKit.vpp.error – 0x2583 (9603)]"],"choices":["Skip App","Stop"]}],"busy":true}'
#         self.status = adapter.Status(json.loads(_status))
#         
#     def test_string(self):
#         s = ('Adding apps on “student-checkout-ipad-10”'
#              ' Step 1 of 27: Assigning a license for “Autodesk ReCap Pro for mobile”')
#         self.assertEquals(s, str(self.status))
# 
#     def test_percentage(self):
#         self.assertEquals('4%', self.status.percentage)
# 
#     def test_progress(self):
#         self.assertEquals('Step 1 of 27', self.status.progress)
# 
#     def test_details(self):
#         s = u'Step 1 of 27: Assigning a license for “Autodesk ReCap Pro for mobile”'
#         self.assertEquals(s, self.status.details)


class TestAlertInit(BaseTestCase):

    def setUp(self):
        s = {u'busy': True,
            u'alerts': [{u'info': [u'The app named \u201cReCap Pro\u201d already exists on \u201cstudent-checkout-ipad-6\u201d.',
                                u'Would you like to replace it with the one you are adding?'], 
                         u'options': [u'Apply to all apps'], 
                         u'choices': [u'Skip App', u'Stop', u'Replace']}], 
            u'activity': {u'info': [u'Step 11 of 27: Transferring placeholder for \u201cReCap Pro\u201d', 
                                 u'Adding apps on \u201cstudent-checkout-ipad-6\u201d'],
                          u'options': [], 
                          u'choices': [u'Cancel']}}
        self.info = s['alerts'][0]
        self.alert = adapter.Alert(self.info)        
        
    def test_message(self):
        expected = self.info['info'][0]
        self.assertEquals(expected, self.alert.message)

    def test_detail(self):
        expected = self.info['info'][1]
        self.assertEquals(expected, self.alert.detail)

    def test_buttons(self):
        expected = self.info['choices']
        self.assertItemsEqual(expected, self.alert.buttons)

    def test_options(self):
        expected = self.info['options']
        self.assertItemsEqual(expected, self.alert.options)

    def test_missing_field(self):
        _info = {'info': ["message"], 'choices':[], 'options': []}
        with self.assertRaises(adapter.Error):
            adapter.Alert(_info)


class TestAlertMock(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        cls._adapter = adapter.acadapter
        def _mockadapter(command, data=None):
            if None in data.values():
                raise adapter.ACAdapterError("failed")
            return (command, data)
        adapter.acadapter = _mockadapter

    @classmethod
    def tearDownClass(cls):
        adapter.acadapter = cls._adapter
         
    def setUp(self):
        alert = {u'info': [u'The app named \u201cReCap Pro\u201d already exists on \u201cstudent-checkout-ipad-6\u201d.',
                           u'Would you like to replace it with the one you are adding?'], 
                 u'options': [u'Apply to all apps'], 
                 u'choices': [u'Skip App', u'Stop', u'Replace']}

        self.info = alert
        self.alert = adapter.Alert(alert)        
    
    def test_dismiss(self):
        expected = ('--action', {'choice':"Stop"})
        self.assertItemsEqual(expected, self.alert.dismiss())

    def test_bad_dismiss(self):
        self.alert.buttons = ["Bad", "Nope"]
        with self.assertRaises(adapter.ACAdapterError):
            self.alert.dismiss()

    def test_dismiss_ok(self):
        self.alert.buttons = ["OK", "Stop", "Cancel"]
        expected = ('--action', {'choice':"OK"})
        self.assertItemsEqual(expected, self.alert.dismiss())


if __name__ == '__main__':
    unittest.main(verbosity=2)
