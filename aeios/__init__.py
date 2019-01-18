# -*- coding: utf-8 -*-

import config
import tethering
from actools import cfgutil, adapter
from device import Device
from tasklist import TaskList
from appmanager import AppManager
from devicemanager import DeviceManager, Stopped

'''Collection of tools for managing and automating iOS devices
'''

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = ('Copyright (c) 2019 '
                 'University of Utah, Marriott Library')
__license__ = 'MIT'
__version__ = '2.6.0'
__url__ = None
__description__ = ('Collection of tools for managing and automating '
                   'iOS devices')
__all__ = [
    'DeviceManager',
    'Stopped',
    'Device',
    'TaskList',
    'AppManager',
    'cfgutil',
    'adapter',
    'tethering']
