#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import time
import signal
import logging

from management_tools import loggers
from ipadmanager import DeviceManager, Stopped

'''Automate the management of iOS devices 
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '2.0.8'
__url__ = None
__description__ = 'Automate the management of iOS devices'

## CHANGE LOG:
# 2.0.1:
#  - fixed a bug causing daemon to stop
# 2.0.2:
#  - modified default location for files
# 2.0.3:
#  - removed encoded quotes added by TextEdit.app
# 2.0.4:
#  - removed manager.run() from checkin() (handled by DeviceManager)
#  - moved adjust_logger_format()
# 2.0.5:
#  - fixed bug that would cause the daemon to quit if a device was erased
# 2.0.6:
#  - added additional exception handling in daemon()
#  - fixed NameError with StoppedError
# 2.0.7:
#  - changed StoppedError to Stopped
# 2.0.8:
#  - changed verification

class SignalTrap(object):
    '''Class for trapping interruptions in an attempt to shutdown
    more gracefully
    '''
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

## DEVICE ACTIONS

def attached(logger, path, info):
    id = os.path.basename(path)
    manager = DeviceManager(id, logger=logger, path=path)
    manager.checkin(info)

def detached(logger, path, info):
    id = os.path.basename(path)
    manager = DeviceManager(id, logger=logger, path=path)
    manager.checkout(info)

def refresh(logger, path):
    id = os.path.basename(path)
    manager = DeviceManager(id, logger=logger, path=path)
    manager.verify()

def daemon(logger, path):
    '''Attempt at script level recursion and daemonization
    Benefits, would reduce the number of launchagents and the 
    Accessiblity access
    '''
    id = os.path.basename(path)
    manager = DeviceManager(id, logger=logger, path=path)
    # start up cfgutil exec with this script as the attach and detach
    # scriptpath 
    cmd = ['/usr/local/bin/cfgutil', 'exec', 
             '-a', "{0} attached".format(sys.argv[0]),
             '-d', "{0} detached".format(sys.argv[0])]
    p = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    
    if p.poll() is not None:
        err = "{0}".format(p.communicate()[1])
        logger.error(err.rstrip())
        raise SystemExit(err)

    sig = SignalTrap(logger)
    while not sig.stopped:

        time.sleep(manager.idle)
        if sig.stopped:
            break

        if p.poll() is not None:
            p = subprocess.Popen[cmd]

        if not manager.stopped:
            try:
                logger.debug("running idle verification")
                manager.verify(run=True)
                logger.debug("idle verification finished")
            except Stopped:
                logger.info("manager was stopped")
            except Exception as e:
                logger.error("unexpected error: {0!s}".format(e))
                
    p.kill()

def adjust_logger_format(logger, pid):
    '''Add the PID to the logger
    '''
    nfmt = '%(asctime)s {0}: %(levelname)s: %(message)s'.format(pid)
    formatter = logging.Formatter(nfmt)
    handler = logger.handlers[0]
    handler.setFormatter(formatter)

def main():
    script = os.path.basename(sys.argv[0])
    scriptname = os.path.splitext(script)[0]
    logger = loggers.StreamLogger(name=scriptname, level=loggers.DEBUG)
    # logger = loggers.FileLogger(name=scriptname, level=loggers.DEBUG)

    # add the PID to the logger
    adjust_logger_format(logger, os.getpid())
    logger.debug("{0} started".format(script))

    app_support = os.path.expanduser('~/Library/Application Support')
    path = os.path.join(app_support, 'edu.utah.mlib.ipad.checkout')
    
    try:
        action = sys.argv[1]
    except IndexError:
        err = "no action was specified"
        logger.error(err)
        raise SystemExit(err)

    # get the iOS Device environment variables set by `cfgutil exec`
    env_keys = ['ECID', 'deviceName', 'bootedState', 'deviceType',
                'UDID', 'buildVersion', 'firmwareVersion', 'locationID']
    info = {k:os.environ.get(k) for k in env_keys}

    if action == 'attached':
        attached(logger, path, info)
    elif action == 'detached':
        detached(logger, path, info)
    elif action == 'refresh':
        refresh(logger, path)
    elif action == 'daemon':
        daemon(logger, path)        
    else:
        err = "invalid action: {0}".format(action)
        logger.error(err)
        raise SystemExit(err)
    
    logger.debug("{0}: {1} finished".format(script, action))
    sys.exit(0)

if __name__ == '__main__':
    main()
