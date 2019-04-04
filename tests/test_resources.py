# -*- coding: utf-8 -*-

import os
import shutil
import logging
import unittest

from aeios import resources

"""
Tests for aeios.resources
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "1.0.0"

LOCATION = os.path.dirname(__file__)
DATA = os.path.join(LOCATION, 'data', 'resources')
TMPDIR = os.path.join(LOCATION, 'tmp', 'resources')


def setUpModule():
    """
    create tmp directory
    """
    try:
        os.makedirs(TMPDIR)
    except OSError as e:
        if e.errno != 17:
            # raise Exception unless TMP already exists
            raise

    # modify module constants
    resources.PREFERENCES = TMPDIR
    resources.PATH = TMPDIR


def tearDownModule():
    """
    remove tmp directory
    """    
    shutil.rmtree(TMPDIR)


class BaseTestCase(unittest.TestCase):
    pass    


class DefaultsTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        BaseTestCase.setUpClass()

    @classmethod
    def tearDownClass(cls):
        BaseTestCase.tearDownClass()
    
    def setUp(self):
        BaseTestCase.setUp(self)
        self.defaults = resources.Defaults()
            
    def tearDown(self):
        BaseTestCase.tearDown(self)

    def test_apps(self):
        self.assertTrue(hasattr(self.defaults, 'apps'))

    def test_aeios(self):
        self.assertTrue(hasattr(self.defaults, 'aeios'))

    def test_devices(self):
        self.assertTrue(hasattr(self.defaults, 'devices'))

    def test_tasks(self):
        self.assertTrue(hasattr(self.defaults, 'tasks'))

    def test_reporting(self):
        self.assertTrue(hasattr(self.defaults, 'reporting'))


class TestFindDefault(DefaultsTestCase):
    
    def test_find_devices(self):
        n = self.defaults.find('devices')
        _id = self.defaults.find('aeios.devices')
        self.assertIsNotNone(n)
        self.assertItemsEqual(n, _id)

    def test_find_apps(self):
        n = self.defaults.find('apps')
        _id = self.defaults.find('aeios.apps')
        self.assertIsNotNone(n)
        self.assertItemsEqual(n, _id)

    def test_find_reporting(self):
        n = self.defaults.find('reporting')
        _id = self.defaults.find('aeios.reporting')
        self.assertIsNotNone(n)
        self.assertItemsEqual(n, _id)

    def test_find_tasks(self):
        n = self.defaults.find('tasks')
        _id = self.defaults.find('aeios.tasks')
        self.assertIsNotNone(n)
        self.assertItemsEqual(n, _id)

    def test_find_preferences(self):
        n = self.defaults.find('preferences')
        _id = self.defaults.find('aeios.preferences')
        self.assertIsNotNone(n)
        self.assertItemsEqual(n, _id)
        self.assertEquals(resources.PREFERENCES, n)

    def test_find_path(self):
        n = self.defaults.find('path')
        _id = self.defaults.find('aeios.path')
        self.assertIsNotNone(n)
        self.assertItemsEqual(n, _id)
        self.assertEquals(resources.PATH, n)

    def test_find_nothing(self):
        with self.assertRaises(TypeError):
            n = self.defaults.find()

    def test_find_empty_string(self):
        with self.assertRaises(resources.MissingDefault):
            n = self.defaults.find('')

    def test_find_None(self):
        with self.assertRaises(AttributeError):
            n = self.defaults.find(None)

    def test_find_no_default(self):
        with self.assertRaises(resources.MissingDefault):
            n = self.defaults.find('aeios.unknown')


class ResourcesTestCase(BaseTestCase):
    """
    Common tests for all resources.Resources()
    """
    @classmethod
    def setUpClass(cls):
        BaseTestCase.setUpClass()
        cls.defaults = {}
        cls.directories = []
        for d in resources.DIRECTORIES:
            cls.directories.append(os.path.join(TMPDIR, d))

    @classmethod
    def tearDownClass(cls):
        BaseTestCase.tearDownClass()
        for d in cls.directories:
            os.rmdir(d)
    
    def setUp(self):
        BaseTestCase.setUp(self)
        resources.DEFAULT.test = {}
        self.resources = resources.Resources('test', path=TMPDIR)
            
    def tearDown(self):
        BaseTestCase.tearDown(self)
        try:
            del(resources.DEFAULT.test)
        except AttributeError:
            pass

        prefs = self.resources.preferences.file
        os.remove(prefs)
        self.assertFalse(os.path.exists(prefs))

        conf = self.resources.config.file
        os.remove(conf)
        self.assertFalse(os.path.exists(conf))

    def assertDomain(self, domain):
        d = "{0}.{1}".format(resources.DOMAIN, domain)
        self.assertEquals(self.resources.domain, d)
        # self.assertTrue(self.resources.domain.endswith(domain))

    def test_config_attr(self):
        self.assertTrue(hasattr(self.resources, 'config'))

    def test_preferences_attr(self):
        self.assertTrue(hasattr(self.resources, 'preferences'))

    def test_domain_attr(self):
        self.assertTrue(hasattr(self.resources, 'domain'))

    def test_idle_attr(self):
        self.assertTrue(hasattr(self.resources, 'idle'))

    def test_path_attr(self):
        self.assertTrue(hasattr(self.resources, 'path'))

    def test_config_exists(self):
        self.assertTrue(os.path.exists(self.resources.config.file))

    def test_preferences_exists(self):
        self.assertTrue(os.path.exists(self.resources.preferences.file))

    def test_paths_created(self):
        for d in self.resources.directories:
            self.assertTrue(os.path.isdir(d))


class TestResourcesInitializaion(ResourcesTestCase):

    def test_no_default_conf(self):
        del(resources.DEFAULT.test)
        with self.assertRaises(resources.MissingDefault):
            r = resources.Resources('test', path=TMPDIR)

    def test_init_no_path(self):
        r = resources.Resources('test')
        self.assertEquals(r.domain, self.resources.domain)
        self.assertEquals(r.path, self.resources.path)
        self.assertEquals(r.config.file, self.resources.config.file)
        self.assertEquals(r.preferences.file, self.resources.preferences.file)
        
    def test_default_conf(self):
        self.assertTrue(os.path.exists(self.resources.config.file))

    def test_default_prefs_exists(self):
        path = self.resources.preferences.file
        self.assertTrue(os.path.exists(path))
    
    def test_default_prefs_value(self):        
        expected = resources.DEFAULT.aeios
        result = self.resources.preferences.read()
        self.assertItemsEqual(result, expected)


class TestResourceProperties(ResourcesTestCase):
    
    def test_wifi_attr(self):
        self.assertTrue(hasattr(self.resources, 'wifi'))

    def test_wifi_value(self):
        expected = os.path.join(TMPDIR, 'Profiles', 'wifi.mobileconfig')
        self.assertEquals(self.resources.wifi, expected)

    def test_key_attr(self):
        self.assertTrue(hasattr(self.resources, 'key'))

    def test_key_value(self):
        expected = os.path.join(TMPDIR, 'Supervision', 'identity.der')
        self.assertEquals(self.resources.key, expected)

    def test_key_attr(self):
        self.assertTrue(hasattr(self.resources, 'cert'))

    def test_key_value(self):
        expected = os.path.join(TMPDIR, 'Supervision', 'identity.crt')
        self.assertEquals(self.resources.cert, expected)


class TestDevicesResource(ResourcesTestCase):
    
    def setUp(self):
        super(ResourcesTestCase, self).setUp()
        self.name = 'aeios.devices'
        self.resources = resources.Resources(self.name)
    
    def test_domain(self):
        self.assertDomain(self.name)

    def test_config(self):
        plist = "{0}.plist".format(self.resources.domain)
        path = os.path.join(TMPDIR, plist)
        self.assertEquals(path, self.resources.config.file)

    def test_config_values(self):
        data = self.resources.config.read()
        defaults = resources.DEFAULT.find(self.resources.domain)
        self.assertItemsEqual(data, defaults)


class TestAppsResources(ResourcesTestCase):
    
    def setUp(self):
        super(ResourcesTestCase, self).setUp()
        self.name = 'aeios.apps'
        self.resources = resources.Resources(self.name)
    
    def test_domain(self):
        self.assertDomain(self.name)

    def test_config(self):
        plist = "{0}.plist".format(self.resources.domain)
        path = os.path.join(TMPDIR, plist)
        self.assertEquals(path, self.resources.config.file)

    def test_config_values(self):
        data = self.resources.config.read()
        defaults = resources.DEFAULT.find(self.resources.domain)
        self.assertItemsEqual(data, defaults)



class TestIdle(ResourcesTestCase):
    
    def test_attr(self):
        self.assertTrue(hasattr(self.resources, 'idle'))

    def test_default_value(self):
        expected = resources.DEFAULT.aeios['Idle']
        self.assertEquals(self.resources.idle(), expected)

    def test_modified_value(self):
        expected = 30
        modified = self.resources.idle(expected)
        self.assertEquals(modified, expected)
        prefs = self.resources.preferences
        self.assertEquals(prefs.get('Idle'), expected)



class TestReporting(ResourcesTestCase):

    def setUp(self):
        ResourcesTestCase.setUp(self)
        self.data = {'Slack': {'URL': 'https://url.test',
                               'channel': '#test-channel',
                               'name': 'test-name'}}

    def test_attr(self):
        self.assertTrue(hasattr(self.resources, 'reporting'))

    def test_default_value(self):
        default = resources.DEFAULT.reporting
        self.assertItemsEqual(self.resources.reporting(), default)
    
    def test_modified_value(self):
        result = self.resources.reporting(self.data)
        self.assertEquals(self.resources.reporting(), result)
        
    def test_modified_values(self):
        """
        test default data is returned
        """        
        result = self.resources.reporting(self.data)
        self.assertItemsEqual(result, self.data)
        self.assertItemsEqual(self.resources.reporting(), self.data)

    def test_update(self):
        new = {'Slack': {'URL': 'https://new.url', 
                         'channel': '#new-channel', 
                         'name': 'new-name'}}
        modified = self.resources.reporting(new)
        self.assertItemsEqual(modified, new)
        self.assertItemsEqual(self.resources.reporting(), new)

    def test_same_reporter(self):
        first = self.resources.reporter
        second = self.resources.reporter
        self.assertIs(first, second)


if __name__ == '__main__':
    fmt = ('%(asctime)s %(process)d: %(levelname)6s: '
           '%(name)s - %(funcName)s(): %(message)s')
    # logging.basicConfig(format=fmt, level=logging.DEBUG)
    # logging.getLogger('aeios.resources.Resources').setLevel(logging.DEBUG)

    unittest.main(verbosity=1)

