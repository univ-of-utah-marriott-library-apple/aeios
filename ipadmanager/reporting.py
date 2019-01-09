# -*- coding: utf-8 -*-

import json
import urllib2

import logging


'''Library for reporting events with device manager
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright(c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '1.0.2'
__url__ = None
__description__ = ('Library for reporting events with devicemanager')

__all__ = [
    'SlackSender',
    'Reporter',
    'Slack',
    'reporterFromSettings'
]

class Error(Exception):
    pass


class Reporter(object):
    '''Base Reporter class
    '''
        
    def __init__(self, *args, **kwargs):
        pass

    def send(self, msg):
        pass


class SlackSender(Reporter):
    '''Minimal functionality of management_tools.slack
    '''
    def __init__(self, url, channel, name, log=None):
        self.log = log if log else logging
        self.url = url
        self.name = name
        self.channel = channel

    def send(self, msg):
        json_str = json.dumps({'text': str(msg), 
                               'username': self.name, 
                               'channel': self.channel})
        try:
            request = urllib2.Request(self.url, json_str)
            urllib2.urlopen(request)
        except Exception as e:
            self.log.error("{0}: unable to send message".format(e))


class Slack(Reporter):
    '''
    '''
    def __init__(self, url, channel, name='ipadmanager', log=None):
        self.log = log if log else logging
        self.url = url
        self.channel = channel
        self.name = name
        self.bot = SlackSender(self.url, self.channel, self.name)
        self.log.debug("slack channel: {0}".format(self.channel))
        self.log.debug("slack name: {0}".format(self.name))
    
    def send(self, msg):
        try:
            self.bot.send(msg)
        except Exception as e:
            self.log.error(e)


def reporterFromSettings(conf, log=None):
    '''Returns appropriate reporter object based upon settings
    '''
    try:
        _slack = conf['Slack']
        name = _slack.get('name')
        return Slack(_slack['url'], _slack['channel'], name, log)
    except KeyError:
        class NullReporter(Reporter):
            pass
        return NullReporter()

