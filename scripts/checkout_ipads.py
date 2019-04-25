#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import signal
import subprocess
import logging
import logging.config

import aeios

# should be replaced with `aeiosutil start`
"""
Run aeios Automation
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = '2.2.1'

SCRIPT = os.path.basename(__file__)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(name)s: %(funcName)s: %(message)s'
        },
        'precise': {
            'format': ('%(asctime)s %(process)d: %(levelname)8s: %(name)s '
                       '- %(funcName)s(): line:%(lineno)d: %(message)s')
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': 'ext://sys.stderr'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'precise',
            'when': 'midnight',
            'encoding': 'utf8',
            'backupCount': 5,
            'filename': None,
        },
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ["file", "console"]
    }
}


class SignalTrap(object):
    """
    Class for trapping interruptions in an attempt to shutdown
    more gracefully
    """
    def __init__(self, logger):
        self.stopped = False
        self.log = logger
        signal.signal(signal.SIGINT, self.trap)
        signal.signal(signal.SIGQUIT, self.trap)
        signal.signal(signal.SIGTERM, self.trap)
        signal.signal(signal.SIGTSTP, self.trap)

    def trap(self, signum, frame):
        self.log.debug("received signal: {0}".format(signum))
        self.stopped = True


# DEVICE ACTIONS

def run(manager):
    """
    Attempt at script level recursion and daemonization
    Benefits, would reduce the number of launchagents and the 
    Accessiblity access
    """
    logger = logging.getLogger(SCRIPT)
    logger.info("starting automation")
    # start up cfgutil exec with this script as the attach and detach
    # scriptpath 
    # FUTURE: controller.monitor()
    cmd = ['/usr/local/bin/cfgutil', 'exec', 
             '-a', "{0} attached".format(sys.argv[0]),
             '-d', "{0} detached".format(sys.argv[0])]
    try:
        logger.debug("> %s", " ".join(cmd))
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    except OSError as e:
        if e.errno == 2:
            err = 'cfgutil missing... install automation tools'
            logger.error(err)
            raise SystemExit(err)
        logger.critical("unable to run command: %s", e, exc_info=True)
        raise
        
    if p.poll() is not None:
        err = "{0}".format(p.communicate()[1]).rstrip()
        logger.error(err)
        raise SystemExit(err)

    sig = SignalTrap(logger)
    while not sig.stopped:
        time.sleep(manager.idle)
        if sig.stopped:
            break
        ## restart the cfgtuil command if it isn't running
        if p.poll() is not None:
            p = subprocess.Popen[cmd]
        ## As long as the manager isn't stopped, run the verification
        if not manager.stopped:
            try:
                logger.debug("running idle verification")
                manager.verify(run=True)
                logger.debug("idle verification finished")
            except aeios.Stopped:
                logger.info("manager was stopped")
            except Exception as e:
                logger.exception("unexpected error occurred")
    # terminate the cfutil command
    p.kill()
    logger.info("finished")


def main():
    resources = aeios.resources.Resources()
    logfile = os.path.join(resources.logs, "checkout_ipads.log")
    LOGGING['handlers']['file']['filename'] = logfile
    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger(SCRIPT)
    
    logger.debug("started")
    
    logger.debug("loading DeviceManager")
    manager = aeios.DeviceManager()

    try:
        action = sys.argv[1]
    except IndexError:
        run(manager)
        sys.exit(0)
    
    # get the iOS Device environment variables set by `cfgutil exec`
    env_keys = ['ECID', 'deviceName', 'bootedState', 'deviceType',
                'UDID', 'buildVersion', 'firmwareVersion', 'locationID']
    info = {k:os.environ.get(k) for k in env_keys}
    
    logger.debug("performing action: %s", action)
    
    if action == 'attached':
        manager.checkin(info)
    elif action == 'detached':
        manager.checkout(info)
    elif action == 'refresh':
        manager.verify()
    else:
        err = "invalid action: {0}".format(action)
        logger.error(err)
        raise SystemExit(err)


if __name__ == '__main__':
    main()
