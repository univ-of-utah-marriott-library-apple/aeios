# -*- coding: utf-8 -*-
 
import os
import re
import json
import time
import logging
import subprocess
import datetime as dt

'''Apple Configurator 2 GUI Adapter
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '2.1.0'
__url__ = None
__description__ = 'Apple Configurator 2 GUI Adapter'


# 2.0.1:
#  - modified logging to use default logging
#  - added _record

# add default NullHandler for logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

## dynamic find path to ACAdapter.scpt
LOCATION = os.path.dirname(__file__)
ACADAPTER = os.path.join(LOCATION, 'scripts/ACAdapter.scpt')

## record raw execution info (adapater.log = '/path/to/execution.log')
log = None
    

class Error(Exception):
    pass


class ACAdapterError(Error):
    pass


class ACStallError(Error):
    def __init__(self, activity, t, info):
        self.text = activity['info']
        self.buttons = activity['choices']
        self.time = t
        self.count = info['count']


class ACAlertError(Error):
    def __init__(self, status):
        self.alerts = status['alerts']
        self.activity = status['activity']['info']
        # multiple alerts can be reported
        alert = self.alerts[-1]
        self.buttons = alert['choices']
        self.checkboxes = alert['options']
        self.text = alert['info']

    def __str__(self):
        return "{0}".format(" ".join(self.text))


class RecoveryError(Error):
    def __init__(self, status):
        self.alerts = status['alerts']
        self.activity = status['activity']['info']
        # multiple alerts can be reported
        alert = self.alerts[-1]
        self.buttons = alert['choices']
        self.checkboxes = alert['options']
        self.text = alert['info']


class Status(object):
    '''
    Object to represent an ACAdapter status
    '''
    ## ideas:
#     with ACStatus() as ac:
#         if ac.alert:
#             # handle alert
#             
#         while ac.busy:
            
    
    def __init__(self, timeout=300):
        now = dt.datetime.now()
        self._started = now
        self.timeout = now + dt.timedelta(seconds=timeout)
        self._refresh = None

        self._status = None
        self._previous = []
        self.alerts = []
        self.details = None
        self.step = None
        self.task = None
        self._update(acadapter('--status'))

    def _update(self, _status, timestamp=None):
        self._status = _status
        now = timestamp if timestamp else dt.datetime.now()
        self._timestamp = now
        self._refresh = now + dt.timedelta(seconds=10)

        self.busy = _status['busy']
        self.alerts = [Alert(x) for x in _status['alerts']]
        activity = _status['activity']
        self.details = activity['info'][0]
        self.step, self.action = self.details.split(': ')
        self.task = activity['info'][1]
        
    def __str__(self):
        message = self.task.encode('utf-8')
        details = self.details.encode('utf-8')
        return "{0} {1}".format(message, details)

    @property
    def progress(self):
        '''Returns current progress as a percentage string
        '''
        m = re.match(r'Step (\d+) of (\d+)', self.step)
        v = float(m.group(1)) / int(m.group(2))
        return "{0:.0f}%".format(v*100)

    @property
    def _last_change(self):
        '''
        return seconds since last change
        '''
        return 30
        
    @property
    def stalled(self):
        '''
        Compare previous status to determine if stalled
        '''
        now = dt.datetime.now()
        return (self._last_change > 300) or now > self.timeout
        
    def update(self, timestamp=None):
        self._previous.append(self._status)
        _status = acadapter('--status')
        self._update(_status, timestamp)
    
    def refresh(self, force=False):
        now = dt.datetime.now()
        if force or now > self._refresh:
            self.update(timestamp=now)
    

class Alert(Error):
    '''
    ACAdapter Alert
    '''

    def __init__(self, data):
        self._data = data
        try:
            self.message = data['info'][0]
            self.detail = data['info'][1]
        except IndexError:
            raise Error("missing alert info")
        self.options = data['options']
        self.buttons = data['choices']

    def __repr__(self):
        return self._data

    def __str__(self):
        message = self.message.encode('utf-8')
        details = self.detail.encode('utf-8')
        return "{0} {1}".format(message, details)

    #TO-DO: need a ton of errors to test comparisons
    # def __eq__(self, x):
    #     pass
        
    def dismiss(self):
        choice = None
        for b in ["OK", "Cancel", "Stop"]:
            if b in self.buttons:
                choice = b
                break
        try:
            return acadapter('--action', {'choice':choice})
        except ACAdapterError as e:
            logger = logging.getLogger(__name__+'.Alert')
            logger.error("unable to dismiss alert")
            logger.debug("buttons: %r", self.buttons)
            logger.debug("choice: %r", choice)
            raise   


def _record(file, info):
    logger = logging.getLogger(__name__)
    logger.debug("recording execution: %r", file)

    if not os.path.exists(file):
        try:
            dir = os.path.dirname(file)
            os.makedirs(os.path.dirname(file))
        except OSError as e:
            if e.errno != 17 or not os.path.isdir(dir):
                logger.error("failed to create directory: %r", dir)
                raise
        with open(file, 'w+') as f:
            f.write("{0}\n".format(info))
    else:
        with open(file, 'a+') as f:
            f.write("{0}\n".format(info))

def acadapter(command, data=None):
    logger = logging.getLogger(__name__)

    # build the command
    cmd = ['/usr/bin/caffeinate', '-d', '-i', '-u']
    cmd += [ACADAPTER, command]

    # convert python to JSON for ACAdapter.scpt
    if data:
        j = json.dumps(data)
        cmd += [json.dumps(data)]

    logger.info("> {0}".format(" ".join(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    out, err = p.communicate()
    logger.debug("  OUT: %r", out)
    logger.debug("ERROR: %r", err)

    if log:
        # record everything to specified file (if cfgutil.log)
        try:
            _record(log, {'execution': cmd, 'output': out, 'error': err,
                       'ecids': ecids, 'data': data, 'command': command,
                       'returncode': p.returncode})
        except:
            logger.warning("failed to record execution", exc_info=True)

    if p.returncode != 0:
        _script = os.path.basename(ACADAPTER)
        logger.error("%s: %s", _script, err.rstrip())
        logger.debug("returncode: %d", p.returncode)
        raise ACAdapterError(err.rstrip())

    result = {}
    if out:
        logger.debug("loading JSON: %r", out)
        result = json.loads(out)
        logger.debug("JSON successfully loaded")
    else:
        logger.debug("no output to load")

    return result

def monitor_run(command, args, poll=5, timeout=300):
    # keeps track of what is running and how long (raises errors if
    # the command is thought to have stalled or raises alert)
    # should also have mechanism to re-attach to existing command
    # this is both terrifying and alluring 
    logger = logging.getLogger(__name__)
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

def recover_old(err, skip=False):
    '''Uses library of possible recovery attempts (needs to be built)
    '''
    logger = logging.getLogger(__name__)
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

def recovery(alert):
    '''
    Returns choice and options for known alerts
    '''
    logger = logging.getLogger(__name__)
    logger.debug("attempting to recover")
    choice = None
    options = []
    report = False
    ## existing App
    if ("already exists" in alert.message) and ("Would you like to replace it" in alert.detail):
        
        if "Apply to all apps" in alert.options:
            options.append("Apply to all apps")
        
        if "Skip App" in alert.choices:
            choice = "Skip App"
        elif "Replace" in alert.choices:
            choice = "Replace"
    ## VPP Store
    elif "An unexpected network error occurred" in alert.detail:
        if "Try Again" in alert.choices:
            choice = "Try Again"
        elif "Stop" in alert.choices:
            choice = "Stop"
        else:
            choice = "Cancel"
    else:
        logger.error("unknown alert: %s", alert)
        logger.debug("choices: %r", alert.choices)
        logger.debug("options: %r", alert.options)
        choice = "Stop" if "Stop" in alert.choices else "Cancel"
        logger.info("attempting to %s", choice)
        action(choice)
        raise RecoveryError("unknown alert occurred", alert)

    return choice, options
    
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
        raise Error("not a list: {0!r}".format(udids))
    elif not isinstance(apps, type([])):
        raise Error("not a list: {0!r}".format(apps))

    if not apps:
        raise Error("no apps were specified")
    elif not udids:
        raise Error("no UDIDs were specified")

    logger = logging.getLogger(__name__)
    logger.info("installing VPP apps")
    logger.debug("UDIDs: %r", udids)
    logger.debug("Apps: %r", apps)

    status = Status()
    if is_busy():
        status = S
        try:
            choice, options = recovery(e)
            logger.debug("recovery: %r: %r", choice, actions)
            # perform the action returned by recovery()
            action(choice, options)
        except RecoveryError:
            logger.error("unable to recover")
            #TO-DO: log the error
            # re-raise the first error
            raise e
        raise ACAdapterError(err)
    args = {'udids':udids, 'apps':apps}
    if wait:
        try:
            monitor_run('--vppapps', args)
        except ACAlertError as e:
            logger.info("attempting recovery")
            # recover(e, skip)
            try:
                choice, options = recovery(e)
                logger.debug("recovery: %r: %r", choice, actions)
                # perform the action returned by recovery()
                action(choice, options)
            except RecoveryError:
                logger.error("unable to recover")
                #TO-DO: log the error
                # re-raise the first error
                raise e
            monitor_run(None, {'current': e.activity, 'count':0})
    else:
        return acadapter('--vppapps', args)

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
