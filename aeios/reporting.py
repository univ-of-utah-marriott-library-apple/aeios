# -*- coding: utf-8 -*-

import json
import urllib2
import logging

'''Library for reporting events with device manager
'''

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = ('Copyright(c) 2019 '
                 'University of Utah, Marriott Library')
__license__ = 'MIT'
__version__ = '1.0.5'
__url__ = None
__description__ = 'Library for reporting events with devicemanager'

__all__ = [
    'SlackSender',
    'Reporter',
    'NullReporter',
    'Slack',
    'reporterFromSettings'
]

## LOGGING
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(logging.NullHandler())

  
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
    def __init__(self, url, channel, name):
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
    '''Class for sending messages via Slack
    '''
    def __init__(self, url, channel, name=None):
        self.log = logging.getLogger(__name__)
        self.url = url
        self.channel = channel
        self.name = name if name else __name__
        self.log.debug("\n".join(["Slack Reporter:", 
                            "     name: {0}".format(self.name),
                            "      url: {0}".format(self.url),
                            "  channel: {0}".format(self.channel)]))
        self.bot = SlackSender(url, channel, name)
    
    def send(self, msg):
        try:
            self.bot.send(msg)
        except Exception as e:
            self.log.exception("failed to send message: %s", msg)


def reporterFromSettings(info):
    '''Returns appropriate reporter object based upon settings
    '''
    logger = logging.getLogger(__name__)
    logger.info("building reporter")
    logger.debug("settings: %s", info)
    try:
        _slack = info['Slack']
        name = _slack.get('name')
        return Slack(_slack['url'], _slack['channel'], name)
    except KeyError as e:
        logger.error("missing key: %s", e)
        logger.debug("returning NullReporter()")
        return NullReporter()


if __name__ == '__main__':
    pass
