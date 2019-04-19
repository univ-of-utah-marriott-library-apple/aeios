# -*- coding: utf-8 -*-

import os
import sys
import shutil
import logging
import unittest
# import subprocess

from aeios import utility
from aeios import resources

"""
Tests for aeios.utility
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "1.0.0"

LOCATION = os.path.dirname(__file__)
# DATA = os.path.join(LOCATION, 'data', 'aeiosutil')
TMPDIR = os.path.join(LOCATION, 'tmp', 'aeiosutil')
PREFERENCES = os.path.join(TMPDIR, 'Preferences')

def setUpModule():
    """
    create tmp directory
    """
    try:
        os.makedirs(TMPDIR)
        os.mkdir(PREFERENCES)
    except OSError as e:
        if e.errno != 17:
            # raise Exception unless TMPDIR already exists
            raise
    # modify module constants
    resources.PATH = TMPDIR
    resources.PREFERENCES = PREFERENCES
    

def tearDownModule():
    """
    remove tmp directory
    """
    shutil.rmtree(TMPDIR)


class SuppressStderr(object):
    """
    Class to temporarily suppress sys.stderr

    >>> with SuppressStderr():
    ...     print("stderr is suppressed", file=sys.stderr)
    ...     print("stdout is not suppressed", file=sys.stdout)
    ... 
    stdout is not suppressed
    >>> print("stderr has been restored", file=sys.stderr)
    stderr has been restored
    >>> 
    """
    def __init__(self):
        """
        save sys.stderr and open os.devnull
        """
        self.stderr = sys.stderr
        self.devnull = open(os.devnull, 'w')
        
    def __enter__(self):
        """
        replace sys.stderr with os.devnull
        """
        sys.stderr = self.devnull 
        
    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        restore sys.stderr and close os.devnull
        """
        sys.stderr = self.stderr
        self.devnull.close()


class BaseTestCase(unittest.TestCase):
    pass
    

class ParserTestCase(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        self.parser = utility.Parser()

    def assertNamespace(self, n, data):
        """
        assert Namespace(key='value') == {'key': 'value'}
        """
        ignored = ['verbose', 'debug', 'version']
        namespace = {k: v for k, v in vars(n).items() if k not in ignored}
        self.assertDictEqual(namespace, data)
        
    def assertParsingFails(self, args):
        """
        assert SystemExit is raised while suppressing STDERR
        """
        with self.assertRaises(SystemExit):
            with SuppressStderr():
                self.parser.parse(args)
        
    
class TestAddParser(ParserTestCase):
    
    def setUp(self):
        ParserTestCase.setUp(self)
        self.path = '/path/to/file'
            
    def test_add_missing_item(self):
        """
        test missing ITEM fails: `add`
        """
        args = ('add')
        self.assertParsingFails(args)

    def test_add_unknown_flag(self):
        """
        test unknown flag fails: `add --unknown`
        """
        args = ('add', '--unknown')
        self.assertParsingFails(args)

    def test_add_unknown_item(self):
        """
        test unknown item fails: `add UNKNOWN`
        """
        args = ('add', 'UNKNOWN')
        self.assertParsingFails(args)

    def test_app(self):
        """
        test parsing: `add app NAME`
        """
        args = ('add', 'app', 'NAME')
        expected = {'cmd': 'add', 'item': 'app', 'name': 'NAME'}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_app_missing_name(self):
        """
        test missing app NAME fails: `add app`
        """
        args = ('add', 'app')
        self.assertParsingFails(args)

    def test_app_extra(self):
        """
        test extra app argument fails: `add app NAME EXTRA`
        """
        args = ('add', 'app', 'name', 'EXTRA')
        self.assertParsingFails(args)

    def test_identity_p12(self):
        """
        test identity parsing: `add identity --p12 PATH`
        """
        args = ('add', 'identity', '--p12', self.path)
        expected = {'cmd': 'add', 'item': 'identity', 
                    'p12': True, 'path': self.path}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_identity_p12_order(self):
        """
        test alternative order: `add identity PATH --p12`
        """
        args = ('add', 'identity', self.path, '--p12')
        expected = {'cmd': 'add', 'item': 'identity', 
                    'p12': True, 'path': self.path}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_identity_missing_flag(self):
        """
        test missing identity flag fails: `add identity PATH`
        """
        args = ('add', 'identity', self.path)
        self.assertParsingFails(args)

    def test_identity_p12_missing_path(self):
        """
        test missing identity PATH fails: `add identity --p12`
        """
        args = ('add', 'identity', '--p12')
        self.assertParsingFails(args)

    def test_identity_p12_extra(self):
        """
        test extra identity argument fails: `add identity PATH --p12 EXTRA`
        """
        args = ('add', 'identity', self.path, '--p12', 'extra')
        self.assertParsingFails(args)

    def test_identity_certs(self):
        """
        test identity parsing: `add identity --certs PATH`
        """
        args = ('add', 'identity', '--certs', self.path)
        expected = {'cmd': 'add', 'item': 'identity', 
                    'p12': False, 'path': self.path}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_identity_certs_order(self):
        """
        test alternative order: `add identity PATH --certs`
        """
        args = ('add', 'identity', self.path, '--certs')
        expected = {'cmd': 'add', 'item': 'identity', 
                    'p12': False, 'path': self.path}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_identity_certs_missing_path(self):
        """
        test missing identity PATH fails: `add identity --certs`
        """
        args = ('add', 'identity', '--certs')
        self.assertParsingFails(args)

    def test_identity_p12_extra(self):
        """
        test extra argument fails: `add identity --certs PATH EXTRA`
        """
        args = ('add', 'identity', '--certs', self.path, 'EXTRA')
        self.assertParsingFails(args)

    def test_image_background(self):
        """
        test image parsing: `add image --background PATH`
        """
        args = ('add', 'image', '--background', self.path)
        expected = {'cmd': 'add', 'item': 'image', 
                    'image': 'background', 'path': self.path}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_image_background_order(self):
        """
        test alternative order: `add image PATH --background`
        """
        args = ('add', 'image', self.path, '--background')
        expected = {'cmd': 'add', 'item': 'image', 
                    'image': 'background', 'path': self.path}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_image_alert(self):
        """
        test parsing: `add image --alert PATH`
        """
        args = ('add', 'image', '--alert', self.path)
        expected = {'cmd': 'add', 'item': 'image', 
                    'image': 'alert', 'path': self.path}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_image_alert_order(self):
        """
        test alternative order: `add image PATH --alert`
        """
        args = ('add', 'image', self.path, '--alert')
        expected = {'cmd': 'add', 'item': 'image', 
                    'image': 'alert', 'path': self.path}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_image_lock(self):
        """
        test parsing: `add image --lock PATH`
        """
        args = ('add', 'image', '--lock', self.path)
        expected = {'cmd': 'add', 'item': 'image', 
                    'image': 'lock', 'path': self.path}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_image_lock_order(self):
        """
        test alternative order: `add image PATH --lock`
        """
        args = ('add', 'image', self.path, '--lock')
        expected = {'cmd': 'add', 'item': 'image', 
                    'image': 'lock', 'path': self.path}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_image_missing_flag(self):
        """
        test missing image flag fails: `add image PATH`
        """
        args = ('add', 'image', self.path)
        self.assertParsingFails(args)

    def test_wifi(self):
        """
        test wifi parsing: `add wifi PATH`
        """
        args = ('add', 'wifi', self.path)
        expected = {'cmd': 'add', 'item': 'wifi', 'path': self.path}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_wifi_missing_path(self):
        """
        test missing wifi PATH fails: `add wifi`
        """
        args = ('add', 'wifi')
        self.assertParsingFails(args)

    def test_wifi_extra(self):
        """
        test extra wifi argument fails: `add wifi PATH EXTRA`
        """
        args = ('add', 'wifi', self.path, 'EXTRA')
        self.assertParsingFails(args)


class TestRemoveParser(ParserTestCase):
                
    def test_add_missing_item(self):
        """
        test missing ITEM fails: `remove`
        """
        args = ('remove')
        self.assertParsingFails(args)

    def test_remove_unknown_flag(self):
        """
        test unknown flag fails: `remove --unknown`
        """
        args = ('remove', '--unknown')
        self.assertParsingFails(args)

    def test_remove_unknown_item(self):
        """
        test unknown item fails: `remove UNKNOWN`
        """
        args = ('remove', 'UNKNOWN')
        self.assertParsingFails(args)

    def test_app(self):
        """
        test parsing: `remove app NAME`
        """
        args = ('remove', 'app', 'NAME')
        expected = {'cmd': 'remove', 'item': 'app', 'name': 'NAME'}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_app_missing_name(self):
        """
        test missing app NAME fails: `remove app`
        """
        args = ('remove', 'app')
        self.assertParsingFails(args)

    def test_app_extra(self):
        """
        test extra app argument fails: `remove app NAME EXTRA`
        """
        args = ('remove', 'app', 'name', 'EXTRA')
        self.assertParsingFails(args)

    def test_identity(self):
        """
        test identity parsing: `add identity --p12 PATH`
        """
        args = ('remove', 'identity')
        expected = {'cmd': 'remove', 'item': 'identity'}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_identity_extra(self):
        """
        test extra identity argument fails: `remove identity EXTRA`
        """
        args = ('remove', 'identity', 'EXTRA')
        self.assertParsingFails(args)

    def test_image_background(self):
        """
        test image parsing: `remove image --background`
        """
        args = ('remove', 'image', '--background')
        expected = {'cmd': 'remove', 'item': 'image', 'image': 'background'}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_image_alert(self):
        """
        test parsing: `remove image --alert`
        """
        args = ('remove', 'image', '--alert')
        expected = {'cmd': 'remove', 'item': 'image', 'image': 'alert'}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_image_lock(self):
        """
        test parsing: `remove image --lock`
        """
        args = ('remove', 'image', '--lock')
        expected = {'cmd': 'remove', 'item': 'image', 'image': 'lock'}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_image_all(self):
        """
        test parsing: `remove image --all`
        """
        args = ('remove', 'image', '--all')
        expected = {'cmd': 'remove', 'item': 'image', 'image': 'all'}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_image_missing_flag(self):
        """
        test missing image flag fails: `remove image`
        """
        args = ('remove', 'image')
        self.assertParsingFails(args)

    def test_wifi(self):
        """
        test wifi parsing: `remove wifi`
        """
        args = ('remove', 'wifi')
        expected = {'cmd': 'remove', 'item': 'wifi'}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_wifi_extra(self):
        """
        test extra wifi argument fails: `remove wifi EXTRA`
        """
        args = ('remove', 'wifi', 'EXTRA')
        self.assertParsingFails(args)

    def test_reporting(self):
        """
        test reporting parsing: `remove reporting`
        """
        args = ('remove', 'reporting')
        expected = {'cmd': 'remove', 'item': 'reporting'}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_reporting_extra(self):
        """
        test extra reporting argument fails: `remove reporting EXTRA`
        """
        args = ('remove', 'reporting', 'EXTRA')
        self.assertParsingFails(args)


class TestConfigureSlack(ParserTestCase):
    
    def setUp(self):
        ParserTestCase.setUp(self)
        self.parser = utility.Parser()
        self.url = 'https://slack.url'
        self.channel = '#test-channel'
        self.name = 'test-name'
         
    def test_slack(self):
        """
        test slack default name: 
            `configure slack URL CHANNEL --name NAME`
        """
        args = ('configure', 'slack', self.url, self.channel, 
                '--name', self.name)
        expected = {'cmd': 'configure', 'item': 'slack', 
                    'URL': self.url, 
                    'channel': self.channel, 
                    'name': self.name}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_slack_order(self):
        """
        test alternative order: 
            `configure slack --name NAME URL CHANNEL`
        """
        expected = {'cmd': 'configure', 'item': 'slack', 
                    'URL': self.url, 
                    'channel': self.channel, 
                    'name': self.name}
        args = ('configure', 'slack', '--name', self.name, self.url, 
                self.channel)
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_slack_default_name(self):
        """
        test slack default name: 
            `configure slack URL CHANNEL`
        """
        args = ('configure', 'slack', self.url, self.channel)
        expected = {'cmd': 'configure', 'item': 'slack', 
                    'URL': self.url, 
                    'channel': self.channel, 
                    'name': 'aeios'}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_slack_extra(self):
        """
        test extra slack argument fails: 
            `configure slack URL CHANNEL --name NAME EXTRA`
        """
        args = ('configure', 'slack', self.url, self.channel, 
                '--name', self.name, 'EXTRA')
        self.assertParsingFails(args)


class TestStartandStopParser(ParserTestCase):
    
    def setUp(self):
        ParserTestCase.setUp(self)
            
    def test_start(self):
        """
        test subcommand: `start`
        """
        args = ('start',)
        expected = {'cmd': 'start', 'login': None}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_start_login(self):
        """
        test `start --login` parses
        """
        args = ('start', '--login')
        expected = {'cmd': 'start', 'login': False}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_stop(self):
        """
        test subcommand: `stop`
        """
        args = ('stop',)
        expected = {'cmd': 'stop', 'login': None}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)

    def test_stop_login(self):
        """
        test `stop --login` parses
        """
        args = ('stop', '--login')
        expected = {'cmd': 'stop', 'login': True}
        result = self.parser.parse(args)
        self.assertNamespace(result, expected)



class TestModifications(BaseTestCase):
    
    def setUp(self):
        BaseTestCase.setUp(self)
        self.parser = utility.Parser()
        self.resources = resources.Resources()
        
    def test_slack_modified(self):
        argv = ('configure', 'slack', 'https://slack.url', '#test-channel', 
                '--name', 'test-name')
        args = self.parser.parse(argv)
        data = {'Slack': {'URL': args.URL, 
                          'channel': args.channel, 
                          'name': args.name}}
        self.resources.reporting(data)
        result = self.resources.preferences.read()
        self.assertItemsEqual(result['Reporting'], data)

    def test_reporting_reset(self):
        self.test_slack_modified()
        default = resources.DEFAULT.reporting
        self.resources.reporting(default)
        result = self.resources.preferences.read()
        self.assertItemsEqual(result['Reporting'], default)
        
    

if __name__ == '__main__':
    fmt = ('%(asctime)s %(process)d: %(levelname)6s: '
           '%(name)s - %(funcName)s(): %(message)s')
    # logging.basicConfig(format=fmt, level=logging.DEBUG)
    unittest.main(verbosity=1)

