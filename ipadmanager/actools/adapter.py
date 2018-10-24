# -*- coding: utf-8 -*-
 
import os
import subprocess
import json
import time

'''Apple Configurator 2 GUI Adapter
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '2.0.0'
__url__ = None
__description__ = 'Apple Configurator 2 GUI Adapter'


LOCATION = os.path.dirname(__file__)
ACADAPTER = os.path.join(LOCATION, 'scripts/ACAdapter.scpt')

DEBUG = False
if DEBUG:
    try:
        from management_tools import loggers
        name = __name__
        logger = loggers.StreamLogger(name=name, level=loggers.DEBUG)
    except:
        import logging
        logger = logging.getLogger(__name__)
        logger.addHandler(logging.NullHandler())
else:
    import logging
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())
    

class Error(Exception):
    pass


class ACAdapterError(Error):
    pass


class ACStallError(Error):
    def __init__(self, activity, t, info):
        logger.debug("ACStallError raised")
        self.text = activity['info']
        self.buttons = activity['choices']
        self.time = t
        self.count = info['count']


class ACAlertError(Error):
    def __init__(self, status):
        logger.debug("ACAlertErrror raised")
        self.alerts = status['alerts']
        self.activity = status['activity']['info']
        # multiple alerts can be reported
        alert = self.alerts[-1]
        self.buttons = alert['choices']
        self.checkboxes = alert['options']
        self.text = alert['info']

    def __str__(self):
        return "{0}".format(" ".join(self.text))


class ACRecoveryError(Error):
    def __init__(self, status):
        logger.debug("ACRecoveryErrror raised")
        self.alerts = status['alerts']
        self.activity = status['activity']['info']
        # multiple alerts can be reported
        alert = self.alerts[-1]
        self.buttons = alert['choices']
        self.checkboxes = alert['options']
        self.text = alert['info']


def acadapter(command, data=None):
    cmd = ['/usr/bin/caffeinate', '-d', '-i', '-u']
    cmd += [ACADAPTER, command]
    if data:
        j = json.dumps(data)
        cmd += [json.dumps(data)]
    logger.debug("> {0}".format(" ".join(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        logger.debug("an error occurred")
        logger.debug("ERR: {0}".format(err))
        raise ACAdapterError(err.rstrip())
    logger.debug("OUT: {0}".format(out.rstrip()))
    try:
        return json.loads(out)
    except:
        logger.debug("no output from command")
        return {}

def monitor_run(command, args, poll=5, timeout=300):
    # keeps track of what is running and how long (raises errors if
    # the command is thought to have stalled or raises alert)
    # should also have mechanism to re-attach to existing command
    # this is both terrifying and alluring 

    # use filelock? (might not be necessary)
    if command:
        acadapter(command, data=args)
        udids = args['udids']
        time.sleep(2)
        activity = {'current':None, 'count':0}
    else:
        # get the selected UDIDs if re-running (might not be necessary,
        # but still pretty cool)
        udids = [d['UDID'] for d in list() if d['selected']]
        activity = args
            
    info = status()
        
    while info['busy']:
        logger.debug("waiting on {0}".format(command))
        time.sleep(poll)
        info = status()
        # an error occurred and can be dealt with elsewhere (or not)
        # either way we should exit the loop
        if info['alerts']:
            raise ACAlertError(info)

        if info['activity'] == activity['current']:
            activity['count'] += 1
        else:
            activity['count'] = 1
            activity['current'] = info['activity']
        
        # convert the count and polling time into seconds
        time_running = activity['count'] * poll
        if time_running > timeout:
            raise ACStallError(info['activity'], time_running, activity)


def recover(err, skip=False):
    '''Uses library of possible recovery attempts (needs to be built)
    '''
    logger.debug("attempting to recover")
    if skip:
        options = []
        if "Apply to all apps" in err.checkboxes:
            options.append("Apply to all apps")
        if "Skip App" in err.buttons:
            action("Skip App", options)
            time.sleep(1)
        return
        logger.error("unable to skip")

    if "Stop" in err.buttons:
        action("Stop")
    elif "Cancel" in err.buttons:
        action("Cancel")
    raise err
    
def list():
    '''returns list of device information from Apple Configurator 2
    '''
    return acadapter('--list')

def status():
    '''returns current activity information from Apple Configurator 2
    '''
    return acadapter('--status')

def action(choice, options=[]):
    args = {'choice':choice, 'options':options}
    return acadapter('--action', args)

def is_busy():
    '''returns True if Apple Configurator is actively performing task
    '''
    return acadapter('--status')['busy']

def install_vpp_apps(udids, apps, wait=True, skip=True):
    if not isinstance(udids, type([])):
        raise TypeError("not a list: {0}".format(udids))
    elif not isinstance(apps, type([])):
        raise TypeError("not a list: {0}".format(apps))

    if not apps:
        logger.debug("no apps were specified")
        return
    elif not udids:
        logger.debug("no UDIDs were specified")
        return

    if is_busy():
        err = "unable to install VPP apps while performing other tasks" 
        logger.error(err)
        raise ACAdapterError(err)
    args = {'udids':udids, 'apps':apps}
    if wait:
        try:
            monitor_run('--vppapps', args)
        except ACAlertError as e:
            recover(e, skip)
            monitor_run(None, {'current': e.activity, 'count':0})
    else:
        return acadapter('--vppapps', args)

def cancel():
    return acadapter('--cancel')

def run_blueprint(udids, blueprint, wait=True):
    # should return dict of udids and success boolean
    if is_busy():
        err = "unable to run blueprint while performing other tasks" 
        raise ACAdapterError(err)
    args = {'udids':udids, 'blueprint':blueprint}
    if wait:
        try:
            monitor_run('--blueprint', args)
        except ACAlertError as e:
            recover(e)
            monitor_run(None, {'current': e.activity, 'count':0})
        except ACStallError as e:
            recover(e)
            monitor_run(None, {'current': e.activity, 'count':e.count})
    else:
        return acadapter('--blueprint', args)

if __name__ == '__main__':
    pass
