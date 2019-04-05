# -*- coding: utf-8 -*-

import os
import shutil
import logging
import unittest 

from aeios import apps, device, resources

"""
Tests for aeios.apps
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright(c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "1.0.4"

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

LOCATION = os.path.dirname(__file__)
TMPDIR = os.path.join(LOCATION, 'tmp')
DATA = os.path.join(TMPDIR, 'apps')
TMP = os.path.join(TMPDIR, 'apps')
PREFERENCES = os.path.join(TMP, 'Preferences')
DEBUG = False

def setUpModule():
    """
    create tmp directories
    modify resources
    """
    resources.PATH = TMP
    resources.PREFERENCES = PREFERENCES

    for path in [TMP, PREFERENCES]:
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno == 17:
                pass


def tearDownModule():
    """
    remove tmp directory
    """
    if not DEBUG:
        shutil.rmtree(TMPDIR)


class BaseTestCaseOLD(unittest.TestCase):
    
    file = None
    devices = [{'UDID':'aabbccddeeff0011223344556677889900000001',
                'ECID':'0x00000000000001', 'deviceType':'iPad7,5'},
               {'UDID':'aabbccddeeff0011223344556677889900000002',
                'ECID':'0x00000000000002', 'deviceType':'iPad7,3'},
               {'UDID':'aabbccddeeff0011223344556677889900000003',
                'ECID':'0x00000000000003', 'deviceType':'iPad12,8'}]

    @classmethod
    def setUpClass(cls):
        cls.tmp = TMP

        cls.resources = resources.Resources()

        ipad, ipadpro, newipad = cls.devices
        devicepath = cls.resources.devices
        cls.ipad = device.Device(ipad['ECID'], ipad, path=devicepath)
        cls.ipadpro = device.Device(ipadpro['ECID'], ipadpro, path=devicepath)
        cls.newipad = device.Device(newipad['ECID'], newipad, path=devicepath)

        cls.manager = apps.AppManager('test', cls.resources)
        cls.file = cls.manager.file
        
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.resources.devices)
        os.remove(cls.file)
        
    def setUp(self):
        cls = self.__class__
        self.ipad = cls.ipad
        self.ipadpro = cls.ipadpro
        self.newipad = cls.newipad
        self.apps = cls.manager
    
    def tearDown(self):
        pass


class BaseTestCase(unittest.TestCase):
    
    file = None
    devices = [{'UDID':'aabbccddeeff0011223344556677889900000001',
                'ECID':'0x00000000000001', 'deviceType':'iPad7,5'},
               {'UDID':'aabbccddeeff0011223344556677889900000002',
                'ECID':'0x00000000000002', 'deviceType':'iPad7,3'},
               {'UDID':'aabbccddeeff0011223344556677889900000003',
                'ECID':'0x00000000000003', 'deviceType':'iPad12,8'}]

    @classmethod
    def setUpClass(cls):
        cls.resources = resources.Resources('aeios.apps')
        
    @classmethod
    def tearDownClass(cls):
        if not DEBUG:
            try:
                shutil.rmtree(cls.resources.path)
            except OSError as e:
                if e.errno == 2:
                    pass
        
#     def setUp(self):
#         self.resources = self.__class__.resources
#     
#     def tearDown(self):
#         try:
#             os.remove(self.resources.config.file)
#         except OSError as e:
#             if e.errno == 2:
#                 pass


# @unittest.skip("Not Finished")
class AppTest(BaseTestCase):
    """
    generic tests for aeios.apps.App
    """
    pass


class AppListTest(BaseTestCase):
    """
    generic tests for aeios.apps.AppList
    """
    def setUp(self):
        BaseTestCase.setUp(self)
        self.applist = apps.AppList()
    
    def test_names(self):
        """
        test apps.AppList().names returns a list
        """
        self.assertIsInstance(self.applist.names, list)


class EmptyAppList(AppListTest):
    
    def test_empty_list_is_false(self):
        """
        test empty AppList() == False
        """
        self.assertFalse(self.applist)

    def test_empty_list_is_not_true(self):
        """
        test empty AppList() != True
        """
        self.assertTrue(not self.applist)


# @unittest.skip("Not Finished")
class ErrorTest(BaseTestCase):
    """
    generic tests for aeios.apps.AppList
    """
    pass


class AppManagerTest(BaseTestCase):
    """
    Generic Tests for AppManagers
    """

    @classmethod
    def setUpClass(cls):
        """
        Only create device records once per TestCase
        """
        super(AppManagerTest, cls).setUpClass()

        ipad7_5 = {'UDID': 'aabbccddeeff0011223344556677889900000001',
                   'ECID': '0x00000000000001', 'deviceType': 'iPad7,5'}
        ipad7_3 = {'UDID': 'aabbccddeeff0011223344556677889900000002',
                   'ECID': '0x00000000000002', 'deviceType': 'iPad7,3'}
        ipad8_1 = {'UDID': 'aabbccddeeff0011223344556677889900000003',
                   'ECID': '0x00000000000003', 'deviceType': 'iPad8,1'}
        ipadf_n = {'UDID': 'aabbccddeeff0011223344556677889900000004',
                   'ECID':'0x00000000000004', 'deviceType': 'iPad128,65'}

        cls.ipad = device.Device(ipad7_5['ECID'], ipad7_5, 
                                  path=cls.resources.devices)
        cls.ipadpro = device.Device(ipad7_3['ECID'], ipad7_3, 
                                     path=cls.resources.devices)
        cls.ipadpro2 = device.Device(ipad8_1['ECID'], ipad8_1, 
                                      path=cls.resources.devices)
        cls.newipad = device.Device(ipadf_n['ECID'], ipadf_n, 
                                     path=cls.resources.devices)
        
        cls.manager = apps.AppManager('test')
    
    def setUp(self):
        BaseTestCase.setUp(self)
        self.resources = resources.Resources('aeios.apps')
        self.apps = self.__class__.manager
    
    def test_resources_exist(self):
        self.assertTrue(os.path.exists(self.apps.config.file))
    
# @unittest.skip("blah")
class TestAppManagerGroups(AppManagerTest):

    def setUp(self):
        AppManagerTest.setUp(self)
        self.apps = apps.AppManager('base-test', self.resources)
        self.file = self.apps.file

    def tearDown(self):
        os.remove(self.file)
    
    def test_groups_with_iPad7_5(self):
        groups = self.apps.groups(self.ipad)
        expected = ['iPads', 'all-iPads']
        self.assertItemsEqual(groups, expected)
        
    def test_groups_with_iPad7_3(self):
        groups = self.apps.groups(self.ipadpro)
        expected = ['iPadPros', 'all-iPads']
        self.assertItemsEqual(groups, expected)
            
    def test_add_apps_to_missing_group(self):
        self.apps.add('custom', ['test', 'test2', 'test3', 'test'])
        result = self.apps.config.read()['custom']
        expected = ['test', 'test2', 'test3']
        self.assertItemsEqual(result, expected)
        self.assertIn('custom', self.apps.groups())
    
    def test_add_apps_to_existing_group(self):
        result = self.apps.add('all-ipads', ['test', 'test2', 'test3', 'test'])
        expected = ['test', 'test2', 'test3']
        self.assertItemsEqual(result, expected)
        
    def test_list_all_apps_for_ipad7_5(self):
        # self.apps.add('all', ['all'])
        self.apps.add('all-iPads', ['all-ipads'])
        self.apps.add('iPadPros', ['pro-apps'])
        apps = self.apps.list(self.ipadpro)
        expected = ['all-ipads', 'pro-apps']
        self.assertItemsEqual(apps, expected)
        
    def test_list_all_apps_for_ipad7_3(self):
        # self.apps.add('all', ['all'])
        self.apps.add('all-iPads', ['all-ipads'])
        self.apps.add('iPads', ['non-pro-apps'])
        apps = self.apps.list(self.ipad)
        expected = ['all-ipads', 'non-pro-apps']
        self.assertItemsEqual(apps, expected)
        
    def test_groups_fails_without_model_attribute(self):
        with self.assertRaises(AttributeError):
            self.apps.groups({})


# @unittest.skip("blah")
class TestRemoveApps(AppManagerTest):
    """
    Tests for removing apps

    test__empty()
    test_no_group()
    test_missing_group()
    test_missing_list()
    test_empty_list()
    tests_remove_all()
    """
    pass


@unittest.skip("blah")
class TestAddApps(AppManagerTest):
    """
    Tests for adding apps

    test_None()
    test_remove_app_string()
    test_remove_app_set()
    test_remove_app_list()
    test_remove_app_tuple()
    test_remove_app_unicode()
    test_empty_list()
    test_not_in_list()
    test_no_group()
    """
    pass


# @unittest.skip("blah")
class TestAppManagerList(AppManagerTest):

    def setUp(self):
        AppManagerTest.setUp(self)
        # self.apps.add('all', ['Slack', 'PowerPoint', 'Word'])
        self.apps.add('all-iPads', ['Box Sync', 'Excel', 'Slack', 'PowerPoint', 'Word'])
        self.apps.add('iPads', ['Something Lite'])
        self.apps.add('iPadPros', ['Something Pro', 'Final Cut Pro'])
        # print(self.apps.config.read())
        # raise SystemExit()

    def tearDown(self):
        AppManagerTest.tearDown(self)

#     @classmethod
#     def setUpClass(cls):
#         super(TestAppManagerList, cls).setUpClass()
#         cls.manager.add('all', ['Slack', 'PowerPoint', 'Word'])
#         cls.manager.add('all-iPads', ['Box Sync', 'Excel'])
#         cls.manager.add('iPads', ['Something Lite'])
#         cls.manager.add('iPadPros', ['Something Pro', 'Final Cut Pro'])

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
        expected = ['Slack', 'PowerPoint', 'Word', 'Box Sync', 'Excel', 
                    'Something Lite']
        result = self.apps.list(self.ipad, exclude=['Missing'])
        self.assertItemsEqual(expected, result)

    def test_list_new_ipad(self):
        expected = ['Box Sync', 'Excel', 'Slack', 'PowerPoint', 'Word']
        result = self.apps.list(self.newipad, exclude=['Missing'])
        self.assertItemsEqual(expected, result)


# @unittest.skip("blah")
class TestAppManagerBreakdown(AppManagerTest):

    @classmethod
    def setUpClass(cls):
        super(cls, cls).setUpClass()
        # cls.manager.add('all', ['Slack', 'PowerPoint', 'Word'])
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
    if DEBUG:
        fmt = ('%(asctime)s %(process)d: %(levelname)6s: '
               '%(name)s - %(funcName)s(): %(message)s')
        logging.basicConfig(format=fmt, level=logging.DEBUG)
        logging.getLogger('aeios.resources').setLevel(logging.CRITICAL)
    unittest.main(verbosity=1)
