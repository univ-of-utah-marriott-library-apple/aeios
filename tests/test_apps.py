# -*- coding: utf-8 -*-

import os
import shutil
import logging
import unittest 

from aeios import apps, device

"""
Tests for aeios.apps
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright(c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "1.0.3"

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

LOCATION = os.path.dirname(__file__)
DATA = os.path.join(LOCATION, 'data', 'devicemanager')
TMPDIR = os.path.join(LOCATION, 'tmp', 'devicemanager')


def setUpModule():
    """
    create tmp directory
    """
    try:
        os.makedirs(TMPDIR)
    except OSError as e:
        if e.errno != 17:
            raise  # raise unless TMPDIR already exists
    
def tearDownModule():
    """
    remove tmp directory
    """
    shutil.rmtree(TMPDIR)


class BaseTestCase(unittest.TestCase):
    
    file = None
    devices = [{'UDID':'00112233445566778899aabbccddeeff00112233',
                'ECID':'0xAABBCCDDEEFF11', 'deviceType':'iPad7,5'},
               {'UDID':'33221100ffeeddccbbaa99887766554433221100',
                'ECID':'0x11FFEEDDCCBBAA', 'deviceType':'iPad7,3'}]

    @classmethod
    def setUpClass(cls):
        cls.tmp = TMPDIR
        cls.devicepath = os.path.join(cls.tmp, 'devices')
        ipad, ipadpro = cls.devices
        cls.ipad = device.Device(ipad['UDID'], ipad, 
                                 path=cls.devicepath)
        cls.ipadpro = device.Device(ipadpro['UDID'], ipadpro, 
                                    path=cls.devicepath)

        class _Resources(object):
            def __init__(self):
                self.path = TMPDIR
                self.logs = os.path.join(TMPDIR, 'logs')
            def __str__(self):
                return self.path

        cls.resources = _Resources()

        cls.manager = apps.AppManager('test', cls.resources)
        cls.file = cls.manager.file
        
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.devicepath)
        os.remove(cls.file)
        
    def setUp(self):
        cls = self.__class__
        self.ipad = cls.ipad
        self.ipadpro = cls.ipadpro
        self.apps = cls.manager
    
    def tearDown(self):
        pass


class TestAppManager(BaseTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.apps = apps.AppManager('base-test', self.resources)
        self.file = self.apps.file

    def tearDown(self):
        os.remove(self.file)
    
    def test_groups_with_iPad7_5(self):
        groups = self.apps.groups(self.ipad)
        expected = ['all', 'iPads', 'all-iPads']
        self.assertItemsEqual(groups, expected)
        
    def test_groups_with_iPad7_3(self):
        groups = self.apps.groups(self.ipadpro)
        expected = ['all', 'iPadPros', 'all-iPads']
        self.assertItemsEqual(groups, expected)
            
    def test_add_apps_to_missing_group(self):
        self.apps.add('custom', ['test', 'test2', 'test3', 'test'])
        result = self.apps.config.read()['custom']
        expected = ['test', 'test2', 'test3']
        self.assertItemsEqual(result, expected)
        self.assertIn('custom', self.apps.groups())
        
    def test_add_apps_to_existing_group(self):
        self.apps.add('all', ['test', 'test2', 'test3', 'test'])
        result = self.apps.config.read()['all']
        expected = ['test', 'test2', 'test3']
        self.assertItemsEqual(result, expected)
        
    def test_list_all_apps_for_ipad7_5(self):
        self.apps.add('all', ['all'])
        self.apps.add('all-iPads', ['all-ipads'])
        self.apps.add('iPadPros', ['pro-apps'])
        apps = self.apps.list(self.ipadpro)
        expected = ['all', 'all-ipads', 'pro-apps']
        self.assertItemsEqual(apps, expected)
        
    def test_list_all_apps_for_ipad7_3(self):
        self.apps.add('all', ['all'])
        self.apps.add('all-iPads', ['all-ipads'])
        self.apps.add('iPads', ['non-pro-apps'])
        apps = self.apps.list(self.ipad)
        expected = ['all', 'all-ipads', 'non-pro-apps']
        self.assertItemsEqual(apps, expected)
        
    def test_groups_fails_without_model_attribute(self):
        with self.assertRaises(AttributeError):
            self.apps.groups({})

class TestRemoveApps(BaseTestCase):
    """
    test__empty()
    test_no_group()
    test_missing_group()
    test_missing_list()
    test_empty_list()
    tests_remove_all()
    """
    pass


class TestAppManagerList(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(cls, cls).setUpClass()
        cls.manager.add('all', ['Slack', 'PowerPoint', 'Word'])
        cls.manager.add('all-iPads', ['Box Sync', 'Excel'])
        cls.manager.add('iPads', ['Something Lite'])
        cls.manager.add('iPadPros', ['Something Pro', 'Final Cut Pro'])

    def test_list_all_apps_for_ipadpro(self):
        expected = ['Slack', 'PowerPoint', 'Word','Box Sync', 'Excel', 
                    'Something Pro', 'Final Cut Pro']
        result = self.apps.list(self.ipadpro)
        self.assertItemsEqual(expected, result)

    def test_list_all_apps_for_ipadpro_excluding_exists(self):
        expected = ['Slack', 'PowerPoint', 'Word', 'Box Sync', 
                    'Something Pro', 'Final Cut Pro']
        result = self.apps.list(self.ipadpro, exclude=['Excel'])
        self.assertItemsEqual(expected, result)

    def test_list_all_apps_for_ipadpro_excluding_missing(self):
        expected = ['Slack', 'PowerPoint', 'Word','Box Sync', 'Excel', 
                    'Something Pro', 'Final Cut Pro']
        result = self.apps.list(self.ipadpro, exclude=['Missing'])
        self.assertItemsEqual(expected, result)

    def test_list_all_apps_for_ipad(self):
        expected = ['Slack', 'PowerPoint', 'Word','Box Sync', 'Excel', 
                    'Something Lite']
        result = self.apps.list(self.ipad)
        self.assertItemsEqual(expected, result)

    def test_list_all_apps_for_ipad_excluding_exists(self):
        expected = ['Slack', 'PowerPoint', 'Box Sync', 'Excel', 
                    'Something Lite']
        result = self.apps.list(self.ipad, exclude=['Word'])
        self.assertItemsEqual(expected, result)

    def test_list_all_apps_for_ipad_excluding_missing(self):
        expected = ['Slack', 'PowerPoint', 'Word','Box Sync', 'Excel', 
                    'Something Lite']
        result = self.apps.list(self.ipad, exclude=['Missing'])
        self.assertItemsEqual(expected, result)


class TestAppManagerBreakdown(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(cls, cls).setUpClass()
        cls.manager.add('all', ['Slack', 'PowerPoint', 'Word'])
        cls.manager.add('all-iPads', ['Box Sync', 'Excel'])
        cls.manager.add('iPads', ['Something Lite'])
        cls.manager.add('iPadPros', ['Something Pro', 'Final Cut Pro'])

    def test_breakdown_returns_list(self):
        devices = [self.ipad, self.ipadpro]
        test = self.apps.breakdown(devices)
        self.assertTrue(isinstance(test, list))

    def test_breakdown_returns_three_instructions(self):
        devices = [self.ipad, self.ipadpro]
        test = self.apps.breakdown(devices)
        self.assertTrue(len(test) == 3)

    def test_breakdown_returns_two_instructions(self):
        devices = [self.ipadpro]
        test = self.apps.breakdown(devices)
        self.assertTrue(len(test) == 2)


if __name__ == '__main__':
    fmt = ('%(asctime)s %(process)d: %(levelname)6s: '
           '%(name)s - %(funcName)s(): %(message)s')
    # logging.basicConfig(format=fmt, level=logging.DEBUG)
    unittest.main(verbosity=1)
