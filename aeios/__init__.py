# -*- coding: utf-8 -*-

import config
import apps
import tethering

from actools import cfgutil, adapter
from device import Device, DeviceList
from tasklist import TaskList
from devicemanager import DeviceManager, Stopped

"""
Automated Enterprise iOS

A collection of tools for managing and automating iOS devices
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "2.8.0"
__all__ = [
    'apps',
    'DeviceManager',
    'Stopped',
    'Device',
    'TaskList',
    'cfgutil',
    'adapter',
    'tethering']
