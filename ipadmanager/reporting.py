# -*- coding: utf-8 -*-

import json
import urllib2
import logging

'''Library for reporting events with device manager
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = ("Copyright(c) 2018 "
                 "University of Utah, Marriott Library")
__license__ = "MIT"
__version__ = '1.0.4'
__url__ = None
__description__ = 'Library for reporting events with devicemanager'

__all__ = [
    'SlackSender',
    'Reporter',
    'Slack',
    'reporterFromSettings'
]

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s')
LOGGER = logging.getLogger(__name__)


class Error(Exception):
    pass


class Reporter(object):
    '''Base Reporter class
    '''
        
    def __init__(self, *args, **kwargs):
        pass

    def send(self, msg):
        pass


class NullReporter(Reporter):
    '''Does nothing
    '''
    pass


class SlackSender(Reporter):
    '''Minimal functionality of management_tools.slack
    '''
    def __init__(self, url, channel, name, log=None):
        self.url = url
        self.name = name
        self.channel = channel

    def send(self, msg):
        json_str = json.dumps({'text': str(msg), 
                               'username': self.name, 
                               'channel': self.channel})
        request = urllib2.Request(self.url, json_str)
        urllib2.urlopen(request)

class Slack(Reporter):
    '''Class for reporting using Slack
    '''
    def __init__(self, url, channel, name='ipadmanager', log=LOGGER):
        self.log = log
        self.url = url
        self.channel = channel
        self.name = name
        self.bot = SlackSender(url, channel, name, log=log)
        self.log.debug("Slack: channel: {0}".format(self.channel))
        self.log.debug("Slack: name: {0}".format(self.name))
    
    def send(self, msg):
        try:
            self.bot.send(msg)
        except Exception as e:
            self.log.error(e)


def reporterFromSettings(conf, log=LOGGER):
    '''Returns appropriate reporter object based upon settings
    '''
    try:
        _slack = conf['Slack']
        name = _slack.get('name')
        return Slack(_slack['url'], _slack['channel'], name, log)
    except KeyError as e:
        log.error("missing key: {0}".format(e))
        log.debug("returning NullReporter()".format(e))
        return NullReporter()

if __name__ == '__main__':
    pass
