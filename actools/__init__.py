# -*- coding: utf-8 -*-

from __future__ import print_function

import logging
import cfgutil
import adapter

__all__ = []

# meant as an abstraction between cfgutil and ACAdapter
# some functionality may come from one or the other, but should stay 
# constant here

def reset(ecids):
    '''Erase and re-enroll specified UDIDs
    '''
    erase(ecids)
    DEPenroll(ecids)

def erase(ecids):
    '''Erases all Content and Settings on specified UDIDs
    '''
    cmd = ['cfgutil', '--ecid', ECID, 'erase']
    pass

def prepareDEP(ecids):
    '''Enroll specified UDIDs in using DEP
    '''
    cfgutil.prepareDEP(ecids)
    cmd = ['cfgutil', '--ecid', ECID, 'prepare', '--dep', 
           '--skip-languange', '--skip-region']

def install_apps(ecids, apps):
    '''Install local apps on specified UDIDs
    '''
    pass

def install_vpp_apps(udids, apps):
    '''Install VPP apps on specified UDIDs
    '''
    adapter.install_vpp_apps(udids, apps)

def install_profile(ecids, profile):
    '''Install profile on spececified UDIDs
    '''
    pass

def install_profiles(ecids, profiles):
    '''Install multiple profiles on specified UDIDs
    '''
    pass

def restart(ecids):
    '''Restart specified UDIDs
    '''
    pass

def shutdown(ecids):
    '''Shutdown specified UDIDs
    '''
    pass
    
def restore(ecids):
    pass

def tag(ecids, tags):
    pass

def wallpaper(ecids, image, screen='both'):
    if screen not in ['both', 'lock', 'home']:
        raise RuntimeError("invalid screen: {0}".format(screen))
    pass

def rename(ecid, name):
    pass

def get(ecids, keys, **kwargs):
    return cfgutil.get(keys, ecids, **kwargs)

def run_blueprint(udids, blueprint):
    # this will need the most work:
    # it would be cool if this could do all the file locking, recover 
    # the alert, and process possible actions (cataloging if possible)
    # it should return a dictionary of udids and whether the blueprint
    # was successful or not
    try:
        return adapter.run_blueprint(udids, blueprint)
    except adapter.ACAdapterError as e:
        pass

    try:
        blueprint.recover(e)
    except BlueprintRecoveryError as e:
        pass

def list():
    return cfgutil.list()

