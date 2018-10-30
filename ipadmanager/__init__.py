# -*- coding: utf-8 -*-

import config
import tethering
from actools import cfgutil, adapter
from device import Device, DeviceError
from tasklist import TaskList
from appmanager import AppManager
from devicemanager import DeviceManager, StoppedError, Slackbot

'''Collection of tools for managing and automating iOS devices
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '2.2.1'
__url__ = None
__description__ = ('Collection of tools for managing and automating '
                   'iOS devices')
__all__ = [
    'StoppedError',
    'DeviceManager',
    'Device',
    'DeviceError',
    'TaskList',
    'AppManager',
    'Slackbot',
    'cfgutil',
    'adapter',
    'tethering',
]

## CHANGELOG:
# 2.0.1:
#   - added Slackbot from devicemanager
# 2.0.2:
#   - Moved Slackbot back to devicemanager
# 2.2.1:
#   - major changes devicemanager, cfgutil, device
