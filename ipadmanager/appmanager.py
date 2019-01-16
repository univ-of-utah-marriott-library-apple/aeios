# -*- coding: utf-8 -*-

import re
import os
import logging

import config

'''Create sets of Apps for iPads
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '2.2.1'
__url__ = None
__description__ = 'Create sets of Apps for iPads'
__all__ = ['AppManager']

## CHANGELOG:
# 2.0.1:
#   - re-arranged functions
#   - added comments
#
# 2.1.0:
#   - added unknown():
#       - takes a list of app names and returns the names that are not
#         currently scoped to the device
# 2.1.1:
#   - fixed bug in unknown that would return all apps
#   - modified list() slightly
#   - added Error class
#   - added tests for unknown
# 2.1.2:
#   - removed old unnecessary code, prepped for release
# 2.2.0:
#   - added remove()
#   - added incomplete tests for remove()

# 2.2.1:
#   - added ipad8,1 model identifier (this needs to be fed in elsewhere)
#   TO-DO:
#       - needs to check for missing device identifiers per launch
class Error(Exception):
    pass


class AppManager(object):
    
    default = {'groups':{'model':{'iPad7,3':['iPadPros'],
                                  'iPad8,1':['iPadPros'],
                                  'iPad7,5':['iPads']}}, 
               'all':[], 
               'all-iPads':[], 
               'iPadPros':[], 
               'iPads':[]}
                     
    def __init__(self, id, path=None, logger=None, **kwargs):
        # needs the manager to ask for installed apps
        # or the list of installed apps needs to be provided <--
        if not logger:
            logger = logging.getLogger(__name__)
            logger.addHandler(logging.NullHandler())
        self.log = logger

        a_id = "{0}.apps".format(id)
        self.config = config.Manager(a_id, path=path, **kwargs)

        # read global App configuration (if any)
        _apps = self.__class__.default
        try:
            g_path = path.replace(os.path.expanduser('~'), '')
            g_config = config.Manager(a_id, path=g_path)
            # repopulate defaults with settings from global config
            _apps = g_config.read()
            # overwrite existing apps with global configuration
            self.config.write(_apps)
        except config.ConfigError:
            self.log.debug("no global configuration for apps")
            pass

        try:
            self._record = self.config.read()
        except config.ConfigError:
            self.config.write(_apps)
            self._record = self.config.read()

        self.file = self.config.file

    @property
    def record(self):
        '''Returns contents of config as read from disk
        '''
        return self.config.read()

    def groups(self, device=None):
        '''return list of groups device belongs to
        '''
        if device is not None:
            # strip device type from model identifier ('iPad7,5' -> 'iPad')
            type = re.match(r'^(\w+?)\d+,\d+$', device.model).group(1)
            groupset = set(['all', "all-{0}s".format(type)])
            # model-only support for now
            _membership = self._record['groups']['model'][device.model]
            groupset.update(_membership)
            return list(groupset)
        return [x for x in self._record.keys() if x != 'groups']
        
    def list(self, device, exclude=[]):
        '''Returns set of all apps scoped for device 
        (excluding specifed)
        '''
        appset = set([])
        for group in self.groups(device):
            appset.update(self._record[group])
        appset.difference_update(exclude)
        return list(appset)

    def membership(self, name):
        '''Some sort of membership mapping (I can't remember)
        '''
        members = {}
        for type,v in self.config.get('groups', {}).items():
            for id, grps in v.items():
                if name in grps:
                    g = members.setdefault(type, [])
                    g.append(id)
        return members
    
    def group(self, name, apps=None, membership=None):
        return {'apps': list(self._record[name]), 
                'members': self.membership(name)}

    def add(self, group, apps):
        '''Mechanism for adding apps to a group
        '''
        _apps = self.config.get(group)
        if not _apps:
            appset = set(apps)
            self.config.update({group: list(appset)})
        else:
            # update existing group apps (excluding duplicates)
            appset = set(_apps + apps)
            self.config.update({group: list(appset)})
        self._record = self.config.read()
        return list(appset)

    def remove(self, group, apps):
        '''Mechanism for removing apps from a group
        '''
        _apps = self.config.get(group)
        if not _apps:
            return []
        else:
            # update existing group apps (excluding duplicates)
            appset = set(_apps) - set(apps)
            self.config.update({group: list(appset)})
        self._record = self.config.read()
        return list(appset)

    def unknown(self, device, apps):
        '''Returns a list of apps that are not scoped for device
        '''
        appset = set(apps)
        return list(appset.difference(self.list(device)))

    def breakdown(self, devices):
        '''I hate this and it's temporary but should (unintelligently)
        return two instruction sets:
             [([<all devices>], [<all ipad apps>]),
             ([<all iPad Pros>], [<all iPad Pro apps>])]
        the second instruction set is only returned if iPad Pros 
        (iPad7,3) are included in the device list 
        '''
        _all = self._record['all']
        _ipads = self._record['all-iPads']

        # create a list of all unique apps for all iPads
        _breakdown = [(devices, list(set(_all).union(_ipads)))]

        if self._record['iPads']:
            ipads = [x for x in devices if x.model == 'iPad7,5']
            if ipads:
                # add second instruction set for iPads (if any)
                # TO-DO: this will add an empty instruction set
                _breakdown.append((ipads, self._record['iPads'])) 

        # check if iPad pros are included in the specified devices
        ipadpros = [x for x in devices if x.model == 'iPad7,3']
        if ipadpros and self._record['iPadPros']:
            # add third instruction set for iPad Pros (if any)
            _breakdown.append((ipadpros, self._record['iPadPros'])) 
        return _breakdown

                  
if __name__ == '__main__':
    pass
