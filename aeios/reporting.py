# -*- coding: utf-8 -*-

import json
import urllib2
import logging

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright(c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "1.0.6"
__all__ = [
    'SlackSender',
    'Reporter',
    'NullReporter',
    'Slack',
    'reporterFromSettings'
]

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

  
class Error(Exception):
    pass


class Reporter(object):
    """
    Base Reporter class
    """
    def send(self, msg):
        #TO-DO: raise NotImplementedError()
        pass


class NullReporter(Reporter):
    """
    Does nothing
    """
    #TO-DO: implement send()
    # def send(self, msg):
    #     pass
    pass
    

#TO-DO: combine SlackBot and Slack
class SlackBot(Reporter):
    """
    Minimal functionality of management_tools.slack
    """
    def __init__(self, url, channel, name):
        self.url = url
        self.name = name
        self.channel = channel

    def send(self, msg):
        json_str = json.dumps({'text': msg,
                               'username': self.name, 
                               'channel': self.channel})
        request = urllib2.Request(self.url, json_str)
        urllib2.urlopen(request)


class Slack(Reporter):
    """
    Class for sending messages via Slack
    """
    def __init__(self, url, channel, name=__name__):
        self.log = logging.getLogger(__name__ + '.Slack')
        self.url = url
        self.channel = channel
        self.name = name
        self.bot = SlackBot(url, channel, name)
    
    def send(self, msg):
        try:
            self.bot.send(msg)
        except:
            self.log.error(u"failed to send message: %s", msg)


def reporterFromSettings(info):
    """
    Returns appropriate Reporter based upon settings
    """
    logger = logging.getLogger(__name__)
    logger.info("building reporter")
    logger.debug("settings: %r", info)
    try:
        _slack = info['Slack']
        name = _slack.get('name')
        return Slack(_slack['URL'], _slack['channel'], name)
    except KeyError as e:
        logger.error("missing key: %s", e)
        logger.debug("returning NullReporter()")
        return NullReporter()


if __name__ == '__main__':
    pass
