# -*- coding: utf-8 -*-

import logging

import config
import tethering
from actools import cfgutil, adapter
from device import Device, DeviceError
from tasklist import TaskList
from appmanager import AppManager
from devicemanager import DeviceManager, StoppedError

try:
    from management_tools import loggers, slack
except ImportError:
    slack = None

'''Collection of tools for managing and automating iOS devices
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '2.0.1'
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

class Slackbot(object):
    '''Null Wrapper for management_tools.slack
    '''
    def __init__(self, info, logger=None):
        if not logger:
            logger = logging.getLogger(__name__)
            logger.addHandler(logging.NullHandler())
        self.log = logger
        try:
            # TO-DO: name could be dynamic
            self.name = info['name']
            self.channel = info['channel']
            self.url = info['url']
            self.bot = slack.IncomingWebhooksSender(self.url, 
                               bot_name=self.name, channel=self.channel)
            self.log.info("slack channel: {0}".format(self.channel))
        except AttributeError as e:
            self.log.error("slack tools not installed")
            self.bot = None            
        except KeyError as e:
            self.log.error("missing slack info: {0}".format(e))
            self.bot = None
    
    def send(self, msg):
        try:
            self.bot.send_message(msg)
        except AttributeError:
            self.log.debug("slack: unable to send: {0}".format(msg))
            pass
