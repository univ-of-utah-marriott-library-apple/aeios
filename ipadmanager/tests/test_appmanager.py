#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import unittest 

'''Tests for ipadmanager.appmanager
'''

from appmanager import AppManager
from device import Device, DeviceError

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '1.0.2'
__url__ = None
__description__ = 'Tests for ipadmanager.appmanager'

## location for temporary files created with tests
TMPDIR = os.path.join(os.path.dirname(__file__), 'tmp')

def setUpModule():
    '''create tmp directory
    '''
    try:
        os.mkdir(TMPDIR)
    except OSError as e:
        if e.errno != 17:
            # raise Exception unless TMP already exists
            raise
    
def tearDownModule():
    '''remove tmp directory
    '''
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
        cls.ipad = Device(ipad['UDID'], ipad, 
                          path=cls.devicepath)
        cls.ipadpro = Device(ipadpro['UDID'], ipadpro, 
                             path=cls.devicepath)
        cls.manager = AppManager('test', path=cls.tmp)
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
        self.apps = AppManager('base-test', path=self.__class__.tmp)
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
        
    def test_group_with_custom(self):
        result = self.apps.group('iPadPros')
        expected = {'apps':[], 'members':{'model':['iPad7,3']}}
        self.assertTrue(result == expected)
    
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


class TestAppManagerUnknown(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(cls, cls).setUpClass()
        cls.manager.add('all', ['Slack', 'PowerPoint', 'Word'])
        cls.manager.add('all-iPads', ['Box Sync', 'Excel'])
        cls.manager.add('iPads', ['Something Lite'])
        cls.manager.add('iPadPros', ['Something Pro', 'Final Cut Pro'])

    def test_unknown_apps_for_ipadpro(self):
        installed = self.apps.list(self.ipadpro) + ['New App']
        expected = ['New App']
        result = self.apps.unknown(self.ipadpro, installed)
        self.assertItemsEqual(result, expected)


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
    unittest.main(verbosity=2)
