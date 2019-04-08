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
__version__ = "1.0.5"

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

LOCATION = os.path.dirname(__file__)
TMPDIR = os.path.join(LOCATION, 'tmp')
DATA = os.path.join(TMPDIR, 'apps')
TMP = os.path.join(TMPDIR, 'apps')
PREFERENCES = os.path.join(TMP, 'Preferences')


def setUpModule():
    """
    modify resources
    create tmp directories
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
    try:
        shutil.rmtree(TMPDIR)
    except OSError as e:
        if e.errno == 2:
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
        try:
            shutil.rmtree(cls.resources.path)
        except OSError as e:
            if e.errno == 2:
                pass
        
    def setUp(self):
        self.resources = self.__class__.resources
    
    def tearDown(self):
        pass


class AppTest(BaseTestCase):
    """
    generic tests for aeios.apps.App
    """
    def setUp(self):
        BaseTestCase.setUp(self)
                     # test app
        self.data = {'test': {'itunesName': u'«Test App»',
                              'bundleVersion': '1.0.1',
                              'displayName': u'… Test App',
                              'bundleIdentifier': 'edu.app.test'},
                     # newer version of test app
                     'test2': {'itunesName': u'Test App …',
                               'bundleVersion': '2.0.2',
                               'displayName': u'… Test App',
                               'bundleIdentifier': 'edu.app.test'},
                     # different app
                     'other': {'itunesName': u'Another App …',
                               'bundleVersion': '1.0.2',
                               'displayName': u'… Another App',
                               'bundleIdentifier': 'edu.app.test.other'}}

        self.app = apps.App(self.data['test'], path=self.resources.apps)
        self.appv2 = apps.App(self.data['test2'], path=self.resources.apps)
        self.other = apps.App(self.data['other'], path=self.resources.apps)
    
    def test_name_attr(self):
        """
        test App has 'name' attribute
        """
        self.assertTrue(hasattr(self.app, 'name'))

    def test_version_attr(self):
        """
        test App has 'version' attribute
        """
        self.assertTrue(hasattr(self.app, 'version'))

    def test_displayname_attr(self):
        """
        test App has 'displayname' attribute
        """
        self.assertTrue(hasattr(self.app, 'displayname'))

    def test_identifier_attr(self):
        """
        test App has 'identifier' attribute
        """
        self.assertTrue(hasattr(self.app, 'identifier'))

    def test_boolean(self):
        """
        test App has 'identifier' attribute
        """
        self.assertTrue(self.app)


class TestAppComparison(AppTest):

    def test_identical_equality(self):
        """
        test identical app is equal
        """
        identical = apps.App(self.data['test'])
        # make sure we aren't comparing the same object
        self.assertIsNot(self.app, identical)
        self.assertTrue(self.app == identical)

    def test_identical_inequality(self):
        """
        test identical app is not unequal
        """
        identical = apps.App(self.data['test'])
        # make sure we aren't comparing the same object
        self.assertIsNot(self.app, identical)
        self.assertFalse(self.app != identical)

    def test_newer_equality(self):
        """
        test App(v1.0.1) == App(v2.0.2) == False
        """
        self.assertFalse(self.app == self.appv2)

    def test_newer_inequality(self):
        """
        test App(v1.0.1) != App(v2.0.2) == True
        """
        self.assertTrue(self.app != self.appv2)

    def test_different_equality(self):
        """
        test app == different == False
        """
        self.assertFalse(self.app == self.other)

    def test_newer_inequality(self):
        """
        test App(1.0.1) != app (2.0.2) == True
        """
        self.assertTrue(self.app != self.appv2)


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


class ErrorTest(BaseTestCase):
    """
    generic tests for aeios.apps.AppList
    """
    pass


class AppManagerTest(BaseTestCase):
    """
    Generic Tests for AppManager
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
                   'ECID':'0x00000000000004', 'deviceType': 'iPad99,9'}

        cls.ipad = device.Device(ipad7_5['ECID'], ipad7_5, 
                                  path=cls.resources.devices)
        cls.ipadpro = device.Device(ipad7_3['ECID'], ipad7_3, 
                                     path=cls.resources.devices)
        cls.ipadpro2 = device.Device(ipad8_1['ECID'], ipad8_1, 
                                      path=cls.resources.devices)
        cls.newipad = device.Device(ipadf_n['ECID'], ipadf_n, 
                                     path=cls.resources.devices)
        
        cls.manager = apps.AppManager()
    
    def setUp(self):
        BaseTestCase.setUp(self)
        self.resources = resources.Resources('aeios.apps')
        self.manager = self.__class__.manager

    def tearDown(self):
        BaseTestCase.tearDown(self)
        os.remove(self.resources.config.file)
    
    def test_resources_exist(self):
        self.assertTrue(os.path.exists(self.manager.config.file))


class TestAppManagerGroups(AppManagerTest):
    
    def test_groups_with_iPad7_5(self):
        groups = self.manager.groups(self.ipad)
        expected = ['iPads', 'all-iPads']
        self.assertItemsEqual(groups, expected)
        
    def test_groups_with_iPad7_3(self):
        groups = self.manager.groups(self.ipadpro)
        expected = ['iPadPros', 'all-iPads']
        self.assertItemsEqual(groups, expected)
            
    def test_add_apps_to_missing_group(self):
        self.manager.add('custom', ['test', 'test2', 'test3', 'test'])
        result = self.manager.config.read()['custom']
        expected = ['test', 'test2', 'test3']
        self.assertItemsEqual(result, expected)
        self.assertIn('custom', self.manager.groups())
    
    def test_add_apps_to_existing_group(self):
        result = self.manager.add('all-ipads', ['test', 'test2', 'test3', 'test'])
        expected = ['test', 'test2', 'test3']
        self.assertItemsEqual(result, expected)
        
    def test_list_all_apps_for_ipad7_5(self):
        # self.manager.add('all', ['all'])
        self.manager.add('all-iPads', ['all-ipads'])
        self.manager.add('iPadPros', ['pro-apps'])
        apps = self.manager.list(self.ipadpro)
        expected = ['all-ipads', 'pro-apps']
        self.assertItemsEqual(apps, expected)
        
    def test_list_all_apps_for_ipad7_3(self):
        # self.manager.add('all', ['all'])
        self.manager.add('all-iPads', ['all-ipads'])
        self.manager.add('iPads', ['non-pro-apps'])
        apps = self.manager.list(self.ipad)
        expected = ['all-ipads', 'non-pro-apps']
        self.assertItemsEqual(apps, expected)
        
    def test_groups_fails_without_model_attribute(self):
        with self.assertRaises(AttributeError):
            self.manager.groups({})


class TestRemoveApps(AppManagerTest):
    """
    Tests for removing apps
    """
    def setUp(self):
        AppManagerTest.setUp(self)
        # str, unicode (no prefix), unicode (w/prefix)
        self.apps = ['test', u'test – 3', u'テスト']
        self.manager.config.update({'all-iPads': self.apps})
        self.manager.config.update({'Custom': self.apps})
        self.assertApps(self.apps, group='all-iPads')
        self.assertApps(self.apps, group='Custom')

    def assertApps(self, apps, group=None):
        if not group:
            raise ValueError("no group was specified")
        result = self.manager.config.get(group)
        self.assertItemsEqual(apps, result)

    def test_remove_None(self):
        """
        test removing None does nothing
        """
        self.manager.remove(None)
        self.assertApps(self.apps, group='all-iPads')
        self.assertApps(self.apps, group='Custom')
    
    def test_remove_no_group(self):
        """
        test removing default group
        """
        self.manager.remove(['test'])
        self.apps.remove('test')
        self.assertNotIn('test', self.apps)
        self.assertApps(self.apps, group='all-iPads')
    
    def test_remove_multiple_groups_as_tuple(self):
        """
        test removing from multiple groups as tuple
        """
        self.manager.remove(['test'], groups=('all-iPads', 'Custom'))

        expected = [x for x in self.apps if x != 'test']
        self.assertApps(expected, group='all-iPads')
        self.assertApps(expected, group='Custom')

    def test_remove_multiple_groups_as_list(self):
        """
        test removing from multiple groups as list
        """
        self.manager.remove(['test'], groups=['all-iPads', 'Custom'])

        expected = [x for x in self.apps if x != 'test']
        self.assertApps(expected, group='all-iPads')
        self.assertApps(expected, group='Custom')

    def test_remove_non_iterable_group(self):
        """
        test non-iterable group raises an error
        """
        with self.assertRaises(TypeError):
            self.manager.remove(['test'], groups=2)
    
    def test_remove_empty_list(self):
        """
        test removing empty list does nothing
        """
        self.manager.remove([], groups=('all-iPads', 'Custom'))
        self.assertApps(self.apps, group='all-iPads')
        self.assertApps(self.apps, group='Custom')
    
    def test_remove_set(self):
        """
        test removing sets is supported
        """
        self.manager.remove(set(['test']), groups=('all-iPads', 'Custom'))
        expected = [x for x in self.apps if x != 'test']
        self.assertApps(expected, group='all-iPads')
        self.assertApps(expected, group='Custom')
    
    def test_remove_tuple(self):
        """
        test removing tuples is supported
        """
        self.manager.remove(('test',), groups=('all-iPads', 'Custom'))
        expected = [x for x in self.apps if x != 'test']
        self.assertApps(expected, group='all-iPads')
        self.assertApps(expected, group='Custom')

    def test_remove_unicode_app(self):
        """
        test removing tuples is supported
        """
        self.manager.remove([u'テスト'], groups=('all-iPads', 'Custom'))
        expected = [x for x in self.apps if x != u'テスト']
        self.assertApps(expected, group='all-iPads')
        self.assertApps(expected, group='Custom')

    def test_remove_string(self):
        """
        test removing string is supported
        """
        self.manager.remove('test', groups=('all-iPads', 'Custom'))
        expected = [x for x in self.apps if x != 'test']
        self.assertApps(expected, group='all-iPads')
        self.assertApps(expected, group='Custom')

    def test_remove_AppList(self):
        """
        test removing AppList is supported
        """
        x = {'itunesName': 'test', 
             'bundleVersion': '1.0', 
             'displayName': 'a test', 
             'bundleIdentifier': 'test.app'}
        app = apps.App(x)
        applist = apps.AppList([app])
        expected = [x for x in self.apps if x != 'test']
        self.manager.remove(applist, groups=('all-iPads', 'Custom'))
        self.assertApps(expected, group='all-iPads')
        self.assertApps(expected, group='Custom')
        

class TestAddApps(AppManagerTest):
    """
    Tests for adding apps
    """
    def test_add_None(self):
        """
        test adding None does nothing
        """
        expected = []
        result = self.manager.add('all-iPads', None)
        self.assertEquals(expected, result)

    def test_None_group(self):
        """
        test adding None does nothing
        """
        with self.assertRaises(TypeError):
            result = self.manager.add(None, ['test'])

    def test_add_empty(self):
        """
        test adding empty list does nothing
        """
        expected = []
        result = self.manager.add('all-iPads', [])
        self.assertEquals(expected, result)

    def test_add_string(self):
        """
        test single string added
        """
        expected = ['test']
        result = self.manager.add('all-iPads', 'test')
        self.assertItemsEqual(expected, result)

    def test_add_set(self):
        """
        test adding set
        """
        expected = ['test', 'test2', 'test3']
        result = self.manager.add('all-iPads', set(expected))
        self.assertItemsEqual(expected, result)    

    def test_add_list(self):
        """
        test adding list
        """
        expected = ['test', 'test2', 'test3']
        result = self.manager.add('all-iPads', expected)
        self.assertItemsEqual(expected, result)    

    def test_add_tuple(self):
        """
        test adding tuple
        """
        expected = ('test', 'test2', 'test3')
        result = self.manager.add('all-iPads', expected)
        self.assertItemsEqual(expected, result)    

    def test_add_unicode_app(self):
        """
        test adding set of strings
        """
        expected = [u'大辞林']
        result = self.manager.add('all-iPads', expected)
        self.assertItemsEqual(expected, result)
        # also verify app was added
        data = self.manager.config.get('all-iPads')
        self.assertItemsEqual(expected, data)
        

class TestAppManagerList(AppManagerTest):

    def setUp(self):
        AppManagerTest.setUp(self)
        self.manager.add('all-iPads', ['Box Sync', 'Excel', 'Slack', 
                                       'PowerPoint', 'Word'])
        self.manager.add('iPads', ['Something Lite'])
        self.manager.add('iPadPros', ['Something Pro', 'Final Cut Pro'])

    def tearDown(self):
        AppManagerTest.tearDown(self)

    def test_list_all_apps_for_ipadpro(self):
        expected = ['Slack', 'PowerPoint', 'Word','Box Sync', 'Excel', 
                    'Something Pro', 'Final Cut Pro']
        result = self.manager.list(self.ipadpro)
        self.assertItemsEqual(expected, result)

    def test_list_all_apps_for_ipadpro_excluding_exists(self):
        expected = ['Slack', 'PowerPoint', 'Word', 'Box Sync', 
                    'Something Pro', 'Final Cut Pro']
        result = self.manager.list(self.ipadpro, exclude=['Excel'])
        self.assertItemsEqual(expected, result)

    def test_list_all_apps_for_ipadpro_excluding_missing(self):
        expected = ['Slack', 'PowerPoint', 'Word','Box Sync', 'Excel', 
                    'Something Pro', 'Final Cut Pro']
        result = self.manager.list(self.ipadpro, exclude=['Missing'])
        self.assertItemsEqual(expected, result)

    def test_list_all_apps_for_ipad(self):
        expected = ['Slack', 'PowerPoint', 'Word','Box Sync', 'Excel', 
                    'Something Lite']
        result = self.manager.list(self.ipad)
        self.assertItemsEqual(expected, result)

    def test_list_all_apps_for_ipad_excluding_exists(self):
        expected = ['Slack', 'PowerPoint', 'Box Sync', 'Excel', 
                    'Something Lite']
        result = self.manager.list(self.ipad, exclude=['Word'])
        self.assertItemsEqual(expected, result)

    def test_list_all_apps_for_ipad_excluding_missing(self):
        expected = ['Slack', 'PowerPoint', 'Word', 'Box Sync', 'Excel', 
                    'Something Lite']
        result = self.manager.list(self.ipad, exclude=['Missing'])
        self.assertItemsEqual(expected, result)

    def test_list_new_ipad(self):
        expected = ['Box Sync', 'Excel', 'Slack', 'PowerPoint', 'Word']
        result = self.manager.list(self.newipad, exclude=['Missing'])
        self.assertItemsEqual(expected, result)


class TestAppManagerBreakdown(AppManagerTest):

    @classmethod
    def setUpClass(cls):
        super(AppManagerTest, cls).setUpClass()
        cls.manager.add('all-iPads', ['Box Sync', 'Excel'])
        cls.manager.add('iPads', ['Something Lite'])
        cls.manager.add('iPadPros', ['Something Pro', 'Final Cut Pro'])

    def test_breakdown_returns_list(self):
        devices = [self.ipad, self.ipadpro]
        test = self.manager.breakdown(devices)
        self.assertTrue(isinstance(test, list))

    def test_breakdown_returns_three_instructions(self):
        devices = [self.ipad, self.ipadpro]
        test = self.manager.breakdown(devices)
        self.assertTrue(len(test) == 3)

    def test_breakdown_returns_two_instructions(self):
        devices = [self.ipadpro]
        test = self.manager.breakdown(devices)
        self.assertTrue(len(test) == 2)


if __name__ == '__main__':
    fmt = ('%(asctime)s %(process)d: %(levelname)6s: '
           '%(name)s - %(funcName)s(): %(message)s')
    # logging.basicConfig(format=fmt, level=logging.DEBUG)
    unittest.main(verbosity=1)
