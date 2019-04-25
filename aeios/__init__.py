# -*- coding: utf-8 -*-

import logging

from . import apps
from . import config
from . import reporting
from . import resources
from . import tethering
from . import utility

from .device import Device, DeviceList
from .devicemanager import DeviceManager, Stopped
from .tasks import TaskList

"""
Automated Enterprise iOS

A collection of tools for managing and automating iOS devices
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "2.9.0"
__all__ = [
    'apps',
    'Device',
    'DeviceList',
    'DeviceManager',
    'Stopped',
    'TaskList',
    'tethering']
