# -*- coding: utf-8 -*-

import os
import logging

from . import config
from . import reporting

"""
Shared resources for aeios
"""

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = '1.0.1'
__all__ = []


# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

# logging2 = {'debug': {'level': logging.DEBUG,
#                       'format': ('%(asctime)s %(process)d: %(levelname)6s: '
#                                  '%(name)s - %(funcName)s(): %(message)s')},
#             'verbose': {'level': logging.INFO,
#                         'format': '%(asctime)s %(levelname)6s: %(message)s'}}
        
# logging = {'level': logging.DEBUG,
#            'format': ('%(asctime)s %(process)d: %(levelname)6s: '
#                       '%(name)s - %(funcName)s(): %(message)s')}

DOMAIN = 'edu.utah.mlib'
PATH = os.path.expanduser('~/Library/aeios')
PREFERENCES = os.path.expanduser('~/Library/Preferences')
DIRECTORIES = ['Apps', 'Devices', 'Images', 'Logs', 'Supervision', 'Profiles']


class Error(Exception):
    pass


class MissingConfiguration(Error):
    """
    Raised if resource is missing
    """
    pass


class MissingDefault(Error):
    """
    Raised if no default value is provided
    """
    pass


class CacheError(Error):
    pass


class Defaults(object):
    
    def __init__(self):
        self.log = logging.getLogger(__name__ + '.Defaults')
    
    def __getattr__(self, attr):
        raise MissingDefault(attr)
    
    def find(self, domain):
        self.log.debug("domain: %r", domain)
        name = domain.split('.')[-1]
        return getattr(self, name)
    
    @property
    def apps(self):
        return {'groups': {'model': {'iPad7,3': ['iPadPros'],
                                    'iPad8,1': ['iPadPros'],
                                    'iPad7,5': ['iPads']}},
               'all-iPads': [],
               'iPadPros': [],
               'iPads': []}
    
    @property
    def aeios(self):
        return {'Idle': 300, 
                'Reporting': self.reporting}
    
    @property
    def tasks(self):
        return {'erase': [], 'prepare': [], 'installapps': [], 'queries': []}
    
    @property
    def reporting(self):
        return {'Slack': {}}

    @property
    def manager(self):
        return {}
    
    @property
    def devices(self):
        return {'Devices': []}
    
    @property
    def path(self):
        return PATH
    
    @property
    def preferences(self):
        return PREFERENCES

# instantiate global object
DEFAULT = Defaults()


class Cache(object):

    def __init__(self):
        self.log = logging.getLogger(__name__ + '.Cache')
        # self.devices = DeviceList()
        # self.conf = conf
                
    @property
    def listed(self):
        return self.conf.get('Devices', [])

    @listed.setter
    def listed(self, value):
        self.conf.update({'Devices': value})

    @property
    def available(self):
        pass
    
    def device(self, ecid):
        for d in self.devices:
            if ecid == d.ecid:
                return d
        raise CacheError("{0!s}: not in cache".format(ecid))
        
    def add(self, device):
        if device not in self.devices:
            self.log.debug("cached device: %s", device)
            self.devices.append(device)


class Resources(object):
        
    def __init__(self, name=None, path=None):
        """            
        """
        self.log = logging.getLogger(__name__ + '.Resources')
        self.path = path if path else PATH
        if name:
            self.domain = "{0}.{1}".format(DOMAIN, name)
            self.log.debug("building config: %r: %r", self.domain, self.path)
            self.config = _config(self.domain, path)
        else:
            self.domain = DOMAIN
        self.preferences = _config('edu.utah.mlib.aeios', PREFERENCES)
        self.auth = None

        # self._cache = None
        self._reporter = None

        for d in DIRECTORIES:
            path = os.path.join(self.path, d)
            setattr(self, d.lower(), path)

        self.directories = build_directories(self.path, DIRECTORIES)

    @property
    def wifi(self):
        """
        :returns: path to wifi.mobileconfig
        """
        return os.path.join(self.profiles, 'wifi.mobileconfig')

    @property
    def key(self):
        """
        :returns: path to identity.der
        """
        return os.path.join(self.supervision, 'identity.der')

    @property
    def cert(self):
        """
        :returns: path to identity.crt
        """
        return os.path.join(self.supervision, 'identity.crt')

    @property
    def reporter(self):
        """
        :return: aeios.reporter
        """
        if not self._reporter:
            data = self.reporting()
            self._reporter = reporting.reporterFromSettings(data)
        return self._reporter

    def idle(self, seconds=None):
        if seconds:
            self.preferences.update({'Idle': seconds})
        return self.preferences.get('Idle')

    def authorization(self):
        """
        :returns: cfgutil.Authentication
        """
        if not self.auth:
            self.log.debug("getting cfgutil authentication")
            self.auth = cfgutil.Authentication(self.key, self.cert)
        return self.auth

    def reporting(self, data=None):
        """
        retrieve and/or set reporting configuration

        :param data:    updates reporting configuration (if provided)
        :returns:       dict containing current reporting configuration
                        raises Missing() if None
        """
        if data:
            self.preferences.update({'Reporting': data})                                
        
        info = self.preferences.get('Reporting')
        if not info:
            raise MissingConfiguration("No configuration for Reporting")
        return info
    
    def __str__(self):
        return self.path


def build_directories(root, names, mode=0o755):
    logger = logging.getLogger(__name__)
    dirs = [os.path.join(root, x) for x in names]
    for d in dirs:
        if not os.path.isdir(d):
            logger.debug("> makedirs: %r (mode=%o)", d, mode)
            os.makedirs(d, mode)
        else:
            logger.debug("directory exists: %r", d)
    return dirs

          
def _config(domain, path=None, defaults=None):
    """
    
    """
    logger = logging.getLogger(__name__)

    # global default variables
    if not path:
        path = PATH
    if not defaults:
        logger.debug("looking for defaults: %r", domain)
        defaults = DEFAULT.find(domain)
        logger.debug("found defaults: %r", defaults)
        
    # TO-DO: this should really support default variables
    # conf = config.Manager(domain, path, defaults)
    conf = config.Manager(domain, path)
    try:
        # if the config doesn't exist, this will raise an error
        conf.read()
    except config.Error as e:
        # logger.error("unable to read config: %s", e)
        logger.debug("creating config: %r", conf.file)
        logger.debug("default: %r", defaults)
        conf.write(defaults)
    return conf


def configure(key, data):
    """
    Modify general configuration
    """
    # configure('Reporting', {'Slack': {'URL': url, 
    #                                   'channel': channel, 
    #                                   'name': name}})
    pass


if __name__ == '__main__':
    pass
