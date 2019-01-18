#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import time
import signal
import logging

import aeios
from management_tools import loggers

'''Automate the management of iOS devices 
'''

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = ('Copyright (c) 2019 '
                 'University of Utah, Marriott Library')
__license__ = 'MIT'
__version__ = '2.1.0'
__url__ = None
__description__ = 'Automate the management of Checkout iOS devices'

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
# 2.0.9:
#  - added cfgutil check in daemon()

# 2.1.0:
#  - modified library name 'ipadmanager' now aeois
#  - changed daemon() to run()
#  - removed 'daemon' flag 
#  - run() is now the default action
#  - manager now instantiated in main()
#  - removed refresh, attached, and detached:
#       - attached(): manager.checkin()
#       - detached(): manager.checkout()
#       - refresh(): manager.verify()
#  - changed working directory to:
#       'Application Support/Checkout iPads'

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

def run(manager, logger):
    '''Attempt at script level recursion and daemonization
    Benefits, would reduce the number of launchagents and the 
    Accessiblity access
    '''
    # start up cfgutil exec with this script as the attach and detach
    # scriptpath 
    # FUTURE: controller.monitor()
    cmd = ['/usr/local/bin/cfgutil', 'exec', 
             '-a', "{0} attached".format(sys.argv[0]),
             '-d', "{0} detached".format(sys.argv[0])]
    try:
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    except OSError as e:
        if e.errno == 2:
            err = 'cfgutil missing... install automation tools'
            logger.error(err)
            raise SystemExit(err)
        raise
        
    if p.poll() is not None:
        err = "{0}".format(p.communicate()[1])
        logger.error(err.rstrip())
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
                logger.error("unexpected error: {0!s}".format(e))                
    ## terminate the cfutil command
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
    resources = os.path.join(app_support, 'Checkout iPads')
    manager = aeios.DeviceManager('edu.utah.mlib.ipad.checkout', 
                                  logger=logger, path=resources)
    try:
        action = sys.argv[1]
    except IndexError:
        run(manager, logger)        
        logger.debug("{0}: run finished".format(script))
        sys.exit(0)

    # get the iOS Device environment variables set by `cfgutil exec`
    env_keys = ['ECID', 'deviceName', 'bootedState', 'deviceType',
                'UDID', 'buildVersion', 'firmwareVersion', 'locationID']
    info = {k:os.environ.get(k) for k in env_keys}

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
    
    logger.debug("{0}: {1} finished".format(script, action))
    sys.exit(0)

if __name__ == '__main__':
    main()
