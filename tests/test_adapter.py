# -*- coding: utf-8 -*-

import os
import json
import shutil
import logging
import unittest
import datetime as dt

from actools import adapter

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "2.0.0"

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

LOCATION = os.path.dirname(__file__)
DATA = os.path.join(LOCATION, 'data', 'adapter')
TMPDIR = os.path.join(LOCATION, 'tmp', 'adapter')


# TestCases
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
        BaseTestCase.setUp(self)
        self.mockfiles = os.path.join(self.data, 'mock')
    
    def lines(self, file):
        with open(file) as f:
            for line in f:
                yield line

    def mock(self, file):
        line = self.lines(file)
        def _mock():
            try:
                _line = next(line)
            except StopIteration:
                return {'activity': None, 'alerts': [], 'busy': False}
            try:
                return json.loads(_line)
            except ValueError:
                raise adapter.ACAdapterError(_line)
        return _mock


class TestStatusStandardRun(MockOutputTestCase):
    
    def setUp(self):
        MockOutputTestCase.setUp(self)
        # self.mockfiles = os.path.join(cls.data, 'mock')
        standardrun = os.path.join(self.mockfiles, 'standard.txt')
        self.status = adapter.Status(callback=self.mock(standardrun))
    
    def test_run(self):
        while self.status.busy:
            self.status.update()
            if self.status.alert:
                raise self.status.alert

               
class TestStatusVPPNetworkError(MockOutputTestCase):
    
    def setUp(self):
        MockOutputTestCase.setUp(self)
        # self.mockfiles = os.path.join(cls.data, 'mock')
        standardrun = os.path.join(self.mockfiles, 'standard.txt')
        self.status = adapter.Status(callback=self.mock(standardrun))
    
    def test_run(self):
        while self.status.busy:
            self.status.update()
            if self.status.alert:
                raise self.status.alert
                

class TestText(BaseTestCase):

    def setUp(self):
        self.data = u"The app named “ReCap Pro” already exists on 3 iPads."
        self.text = adapter.Text(self.data)

    def test_true(self):
        self.assertTrue(self.text)

    def test_has_parts(self):
        self.assertTrue(hasattr(self.text, 'parts'))

    def test_parts_list(self):
        self.assertTrue(isinstance(self.text.parts, list))

    def test_equality(self):
        self.assertEquals(self.data, self.text)


class TestTextEmpty(BaseTestCase):

    def setUp(self):
        self.data = ''
        self.text = adapter.Text('')

    def test_false(self):
        self.assertFalse(self.text)

    def test_has_parts(self):
        self.assertTrue(hasattr(self.text, 'parts'))

    def test_parts_list(self):
        self.assertTrue(isinstance(self.text.parts, list))

    def test_equality(self):
        self.assertEquals(self.data, self.text)


class StatusTestCase(BaseTestCase):

    def setUp(self):
        self.details = (u"Step 11 of 27: "
                        u"Transferring placeholder for “ReCap Pro”")
        self.task = "Adding apps on 4 iPads"
        self.info = {"activity":{"options":[],
                                 "info":[self.details, self.task],
                                 "choices": ["Cancel"]},
                     "alerts": [{"options":["Apply to all apps"],
                                "info":[u"The app named “ReCap Pro” already exists on 3 iPads.",
                                        "Would you like to replace it with the one you are adding?"],
                                "choices": ["Skip App","Skip","Replace","Stop"]}],
                     "busy":True}
        self.timeout = dt.timedelta(seconds=600)
        self.expired = dt.datetime.now() - dt.timedelta(seconds=5)
        self.status = adapter.Status(timeout=600,
                                     callback=lambda: self.info)

    def test_not_stalled(self):
        self.assertFalse(self.status.stalled)

    def test_stalled(self):
        self.status.activity.expiration = self.expired
        self.assertTrue(self.status.stalled)

    def test_alert_true(self):
        self.assertTrue(self.status.alert)

    def test_busy_not_none(self):
        self.assertIsNotNone(self.status.busy)

    def test_task(self):
        self.assertEquals(self.task, self.status.task)

    def test_timeout(self):
        self.assertEquals(self.timeout, self.status.timeout)

    def test_set_timeout(self):
        self.status.timeout = 300
        self.assertEquals(300, self.status.activity.timeout)

    def test_details(self):
        self.assertEquals(self.details, self.status.details)


class TestStatusBusyBlankUpdate(StatusTestCase):
    """
    Tests for when a status updates between tasks where there no
    activity window, but still reports busy
    """

    def setUp(self):
        StatusTestCase.setUp(self)
        blank = {'activity': None, 'alerts':[], 'busy': True}
        # replace status update function with blank one
        self.status._update = lambda: blank
    
    def test_details_not_modified(self):
        details = self.status.details
        self.status.update()
        self.assertEquals(details, self.status.details)

    def test_task_not_modified(self):
        task = self.status.task
        self.status.update()
        self.assertEquals(task, self.status.task)

    def test_still_busy(self):
        self.status.update()
        self.assertTrue(self.status.busy)

    def test_expiration_unmodified(self):
        expiration = self.status.activity.expiration
        self.status.update()
        activity = self.status.activity
        self.assertEquals(self.status.activity.expiration, expiration)


class TestStatusBlank(BaseTestCase):

    def setUp(self):
        blank = {"activity": None, "alerts": [], "busy": False}
        self.status = adapter.Status(callback=lambda: blank)
        self.expired = dt.datetime.now() - dt.timedelta(seconds=5)
    
    def test_activity_is_false(self):
        self.assertFalse(self.status.activity)

    def test_task_is_false(self):
        self.assertIsNone(self.status.task)

    def test_details_are_none(self):
        self.assertIsNone(self.status.details)

    def test_not_busy(self):
        self.assertFalse(self.status.busy)

    def test_alerts_empty_list(self):
        self.assertEquals([], self.status.alerts)

    def test_stalled(self):
        self.status.activity.expiration = self.expired
        self.assertFalse(self.status.stalled)

class PromptTestCase(BaseTestCase):
    """
    Common tests for all adapter.Prompts
    """
    def setUp(self):
        self.message = 'message'
        self.details = 'details'
        self.choices = []
        self.options = []
        self.prompt = adapter.Prompt(self.message, self.details, self.choices, self.options)

    def test_message_attribute(self):
        if hasattr(self, 'prompt'):
            self.assertTrue(hasattr(self.prompt, 'message'))

    def test_message_type(self):
        """
        test prompt.message type is adapter.Text if defined, else None
        """
        if self.prompt.message:
            self.assertIsInstance(self.prompt.message, adapter.Text)
        else:
            self.assertIsNone(self.prompt.message)

    def test_details_attribute(self):
        self.assertTrue(hasattr(self.prompt, 'details'))

    def test_details_type(self):
        """
        test prompt.details type is adapter.Text if defined, else None
        """
        if self.prompt.details:
            self.assertIsInstance(self.prompt.details, adapter.Text)
        else:
            self.assertIsNone(self.prompt.details)

    def test_choices_attribute(self):
        self.assertTrue(hasattr(self.prompt, 'choices'))

    def test_choices_defined(self):
        self.assertIsNotNone(self.prompt.choices)

    def test_choices_type(self):
        self.assertIsInstance(self.prompt.choices, list)

    def test_options_attribute(self):
        self.assertTrue(hasattr(self.prompt, 'options'))

    def test_options_defined(self):
        self.assertIsNotNone(self.prompt.options)

    def test_options_type(self):
        self.assertIsInstance(self.prompt.options, list)


class TestStandardPrompt(PromptTestCase):
    def setUp(self):
        self.data = {"options": ["Apply to all apps"],
                     "info": [u"The app named “ReCap Pro” already exists on 3 iPads.",
                              u"Would you like to replace it with the one you are adding?"],
                     "choices": ["Skip App", "Replace", "Stop"]}

        self.message, self.details = self.data['info']
        self.choices = self.data['choices']
        self.options = self.data['options']
        self.prompt = adapter.Prompt(self.message, self.details,
                                     self.choices, self.options)

    def test_true(self):
        self.assertTrue(self.prompt)

    def test_string(self):
        self.assertEquals(str(self.prompt), str(self.message.encode('utf-8')))


class TestBlankPrompt(PromptTestCase):
    def setUp(self):
        self.message = None
        self.details = None
        self.choices = None
        self.options = None
        self.prompt = adapter.Prompt(self.message, self.details, self.choices, self.options)

    def test_false(self):
        self.assertFalse(self.prompt)


class ActivityTestCase(BaseTestCase):

    def setUp(self):
        self.activity = adapter.Activity(None)
    
    # @unittest.skip("see TestOpenVPPAppActivity")
    # def test_message_defined(self):
    #     self.assertIsNotNone(self.activity.message)
    # 
    # @unittest.skip("see TestOpenVPPAppActivity")
    # def test_details_defined(self):
    #     self.assertIsNotNone(self.activity.details)

    def test_choices_defined(self):
        self.assertIsNotNone(self.activity.choices)

    def test_options_defined(self):
        self.assertIsNotNone(self.activity.options)

    def test_timeout_defined(self):
        self.assertIsNotNone(self.activity.timeout)

    def test_active_defined(self):
        self.assertIsNotNone(self.activity.active)

    def test_expiration_defined(self):
        self.assertIsNotNone(self.activity.expiration)


class TestBlankActivity(ActivityTestCase):
    """
    Test Activity when instantiated with None
    """
    
    def test_message_false(self):
        self.assertFalse(self.activity.message)

    def test_details_false(self):
        self.assertFalse(self.activity.details)

    def test_choices_false(self):
        self.assertFalse(self.activity.choices)

    def test_options_false(self):
        self.assertFalse(self.activity.options)

    def test_active_false(self):
        self.assertFalse(self.activity.active)

    def test_equals_false(self):
        self.assertFalse(self.activity)

    def test_blank_update(self):
        info = {'info': ['details', 'message'], 'choices': ['Cancel'], 'options': []}
        self.activity.update(adapter.Activity(info))
        self.assertTrue(self.activity)
        self.assertEquals(info['info'][1], self.activity.message)
        self.assertEquals(info['info'][0], self.activity.details)
        self.assertEquals(info['choices'], self.activity.choices)
        self.assertEquals(info['options'], self.activity.options)


class TestActivity(ActivityTestCase):

    def setUp(self):
        self.message = "Adding apps on 4 iPads"
        self.details = u"Step 8 of 27: Assigning licenses for “Slack”"
        self.choices = ["Cancel"]
        self.options = []
        self.info = {'info': [self.details, self.message], 
                     'choices': self.choices, 
                     'options': self.options}
        self.activity = adapter.Activity(self.info)
    
    def test_activity_true(self):
        self.assertTrue(self.activity)

    def test_active(self):
        self.assertTrue(self.activity.active)

    def test_message(self):
        self.assertEquals(self.activity.message, self.message)

    def test_details(self):
        self.assertEquals(self.activity.details, self.details)

    def test_choices(self):
        self.assertEquals(self.activity.choices, self.choices)

    def test_options(self):
        self.assertEquals(self.activity.options, self.options)


class TestOpenVPPAppActivity(ActivityTestCase):
    """
    Open VPP app window:
        {'info':[], 'options':[],'choices':['Cancel','Add',u'Choose from my Mac\u2026']}
    """
    def setUp(self):
        # open VPP app window will produce an empty list of info
        self.choices = ['Cancel', 'Add', u'Choose from my Mac\u2026']
        self.options = []
        self.info = {'info': [], 
                     'choices': self.choices, 
                     'options': self.options}
        self.activity = adapter.Activity(self.info)

    def test_choices(self):
        self.assertEquals(self.activity.choices, self.choices)
        

class TestActivityUpdate(BaseTestCase):

    def setUp(self):
        self.message = "Adding apps on 4 iPads"
        self.details = u"Step 8 of 27: Assigning licenses for “Slack”"
        self.choices = ["Cancel"]
        self.options = []
        self.info = {'info': [self.details, self.message], 
                     'choices': self.choices, 
                     'options': self.options}
        self.activity = adapter.Activity(self.info)
    
    def test_blank_update(self):
        self.activity.update(adapter.Activity(None))
        self.assertFalse(self.activity.message)
        self.assertFalse(self.activity.details)
        self.assertFalse(self.activity.options)
        self.assertFalse(self.activity.choices)
        self.assertFalse(self.activity)
        self.assertFalse(self.activity.active)

    def test_update_none(self):
        with self.assertRaises(AttributeError):
            self.activity.update(None)


@unittest.skip("Not Implemented")
class AlertBaseTestCase(BaseTestCase):

    def setUp(self):
        self.data2 = {"options": ["Apply to all apps"],
                      "info": [u"The app named “Teams” already exists on 2 iPads.",
                               u"Would you like to replace it with the one you are adding?"],
                      "choices": ["Skip App", "Replace", "Stop"]}
        self.data3 = {"options": ["Apply to all apps"],
                      "info": [u"The app named “ReCap Pro” already exists on “test-ipad”.",
                               u"Would you like to replace it with the one you are adding?"],
                      "choices": ["Skip App", "Replace", "Stop"]}


class TestAlertInitialization(BaseTestCase):

    def setUp(self):
        self.data = {"info": [u"The app named “ReCap Pro” already exists on 3 iPads.",
                              u"Would you like to replace it with the one you are adding?"],
                     "choices": ["Skip App", "Replace", "Stop"],
                     "options": ["Apply to all apps"]}
        self.message = self.data['info'][0]
        self.details = self.data['info'][1]

        self.alert = adapter.Alert(self.data)

        for attr in ['message', 'details', 'choices', 'options']:
            self.assertTrue(hasattr(self.alert, attr))

    def test_message(self):
        """
        test alert message equals expected string
        """
        self.assertEquals(self.alert.message, self.message)

    def test_details(self):
        """
        test alert details equals expected string
        """
        self.assertEquals(self.alert.details, self.details)

    def test_choices(self):
        """
        test alert choices equals expected list
        """
        self.assertEquals(self.alert.choices, self.data['choices'])

    def test_options(self):
        """
        test alert options equals expected list
        """
        self.assertEquals(self.alert.options, self.data['options'])

    def test_string(self):
        """
        test alert as string
        """
        self.assertEquals(str(self.alert), str(self.message.encode('utf-8')))

    def test_unicode(self):
        """
        test alert as unicode
        """
        self.assertEquals(unicode(self.alert), self.message)


class TestAlertComparison(BaseTestCase):

    def setUp(self):
        self.info = [{"info": [u"The app named “ReCap Pro” already exists on 2 iPads.",
                               u"Would you like to replace it with the one you are adding?"],
                      "choices": ["Skip App", "Replace", "Stop"],
                      "options": ["Apply to all apps"]},
                     {"info": [u"The app named “ReCap Pro” already exists on 2 iPads.",
                               u"Would you like to replace it with the one you are adding?"],
                      "choices": ["Skip App", "Replace", "Stop"],
                      "options": ["Apply to all apps"]},
                     {"info": [u"The app named “Teams” already exists on “test-ipad”.",
                               u"Would you like to replace it with the one you are adding?"],
                      "choices": ["Skip App", "Replace", "Stop"],
                      "options": ["Apply to all apps"]},
                     {"info": [u"The app named “Teams” already exists on “test-ipad”.",
                               u"Would you like to replace it with the one you are adding?"],
                      "choices": ["Skip App", "Replace", "Stop"],
                      "options": ["Apply to all apps"]},
                     {"info": [u"There was a problem communicating with the VPP store.",
                               u"An unexpected network error occurred. Check your internet connection and click Try Again to continue.",
                               u""],
                      "choices": ["Try Again", "Network Diagnostics", "Cancel"],
                      "options": []},
                     {"info": [u"An unexpected error has occurred with “test-ipad-10”.",
                               u"Internal error [ConfigurationUtilityKit.vpp.error – 0x2583 (9603)]"],
                      "choices": ["Skip App", "Stop"],
                      "options": ["Apply to all apps"]}]
        self.alerts = [adapter.Alert(x) for x in self.info]
        self.exists = self.alerts[0]
        self.identical = self.alerts[1]
        self.similar = self.alerts[2]
        self.exists3 = self.alerts[3]
        self.network = self.alerts[4]
        self.unknown = self.alerts[5]

    def test_equality_is(self):
        """
        test alert is equal to itself
        """
        self.assertTrue(self.exists is self.exists)
        self.assertTrue(self.exists == self.exists)

    def test_inequality_is(self):
        """
        test alert is not unequal to itself
        """
        self.assertTrue(self.exists is self.exists)
        self.assertFalse(self.exists != self.exists)

    def test_equaility_identical(self):
        """
        test identical alerts (different objects) are equal to each other
        """
        self.assertFalse(self.exists is self.identical)
        self.assertTrue(self.exists == self.identical)

    def test_inequaility_identical(self):
        """
        test identical alerts (different objects) are NOT unequal to each other
        """
        self.assertFalse(self.exists is self.identical)
        self.assertFalse(self.exists != self.identical)

    def test_equality_unidentical(self):
        """
        test different alerts are NOT equal to each other
        """
        self.assertFalse(self.exists is self.similar)
        self.assertTrue(self.exists != self.similar)

    def test_inequality_unidentical(self):
        """
        test different alerts are unequal to each other
        """
        self.assertFalse(self.exists is self.similar)
        self.assertTrue(self.exists != self.similar)

    def test_equality_different_type(self):
        """
        test not alert == None
        """
        self.assertFalse(self.exists == None)

    def test_inequality_different_type(self):
        """
        test alert != None
        """
        self.assertTrue(self.exists != None)


if __name__ == '__main__':
    unittest.main(verbosity=1)
