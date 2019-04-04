# -*- coding: utf-8 -*-

import os
import re
import json
import time
import logging
import subprocess
import datetime as dt

"""
Apple Configurator 2 GUI Adapter
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2018 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "3.0.0"

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

# dynamic find path to ACAdapter.scpt
ACADAPTER = os.path.join(os.path.dirname(__file__), 'scripts/ACAdapter.scpt')

# record raw execution info (adapter.log = '/path/to/execution.log')
log = None


class Error(Exception):
    pass


class ACAdapterError(Error):
    pass


class ACStalled(Error):
    pass


class StatusError(Error):
    pass


class HandlerError(Error):
    pass


class Text(unicode):
    """
    Unicode wrapper allowing string to be split into parts preserving spaces
    encapsulated by unicode quotation (“ ”)
    """
    regex = re.compile('(“.+?”)| ')

    @property
    def parts(self):
        # split text by whitespace except when encapsulated by u'“ ”'
        return [x for x in re.split(Text.regex, self) if x]


class Prompt(object):
    """
    Base Class for Activity and Alert
    """
    def __init__(self, message, details, choices=None, options=None):
        self.message = Text(message) if message else None
        self.details = Text(details) if details else None
        self.choices = choices if choices else []
        self.options = options if options else []

    def __str__(self):
        try:
            return self.message.encode('utf-8')
        except AttributeError:
            return ''

    def __unicode__(self):
        if self.message is not None:
            return self.message
        else:
            return u''

    def __bool__(self):
        return self.message is not None

    __nonzero__ = __bool__

    def __repr__(self):
        # <adapter.Prompt 0x100543ad0 (u'message', u'details', ["OK"], [])>
        _repr = '<{0}.{1} 0x{2:x} ({3})>'
        p = (self.message, self.details, self.choices, self.options)
        return _repr.format(__name__, self.__class__.__name__,
                            id(self), ", ".join([repr(x) for x in p]))


class Alert(Prompt, Error):

    @classmethod
    def compare(cls, x, y):
        if x == y:
            similarity = 1
        else:
            most = x.parts if len(x.parts) >= len(y.parts) else y.parts
            # compare each part the text and get count of identical parts
            matching = len([a for a, b in zip(x.parts, y.parts) if a == b])
            similarity = float(matching) / len(most)
        return similarity * 100

    def __init__(self, info):
        message = info['info'][0]
        details = info['info'][1]
        Prompt.__init__(self, message, details, info['choices'], info['options'])

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        m = Alert.compare(self.message, other.message)
        d = Alert.compare(self.details, other.details)
        return ((m + d) / 2) == 100

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return Prompt.__repr__(self)

    def similar(self, alert):
        m = Alert.compare(self.message, alert.message)
        d = Alert.compare(self.details, alert.details)
        return ((m + d) / 2) >= 75

    def dismiss(self, callback=None):
        if not callback:
            def callback():
                for choice in ["Cancel", "OK", "Stop"]:
                    if choice in self.choices:
                        action(choice)
                        break
        callback()


class Activity(Prompt):

    def __init__(self, info, timeout=300):
        self.log = logging.getLogger(__name__ + '.Activity')
        self.timeout = dt.timedelta(seconds=timeout)
        self.expiration = dt.datetime.now() + self.timeout
        # TO-DO: fix open VPP app window
        #   {'info':[], 'options':[],'choices':['Cancel','Add',u'Choose from my Mac\u2026']}
        try:
            d, m = info['info'][0:2] if info['info'] else (Text(''), Text(''))
            Prompt.__init__(self, m, d, info['choices'], info['options'])
        except (TypeError, IndexError):
            self.message = Text('')
            self.details = Text('')
            self.choices = []
            self.options = []

    def __bool__(self):
        return self.active

    __nonzero__ = __bool__

    @property
    def active(self):
        if not self.choices:
            return False
        now = dt.datetime.now()
        _active = now <= self.expiration
        self.log.debug("%s <= %s == %s", now, self.expiration, _active)
        return _active

    def update(self, activity):
        self.message = activity.message
        self.choices = activity.choices
        self.options = activity.options
        if self.details != activity.details:
            self.details = activity.details
            self.expiration = dt.datetime.now() + self.timeout
            if self.details:
                self.log.debug("%s: expires: %s", self.details, self.expiration)


class Handler(object):

    def __init__(self, actions=None):
        self.log = logging.getLogger(__name__ + '.Handler')
        if not actions:
            actions = []
        self.actions = actions

    def add_action(self, x):
        self.actions.append(x)

    def process(self, activity=None, alerts=None, busy=True, info=None):
        self.log.debug(u"processing: %s", info)
        
        if not self.actions:
            raise HandlerError("no actions defined")
        
        try:
            self.log.info("performing action")
            for _action in self.actions:
                _action(activity=activity, alerts=alerts, busy=busy, info=info)
        except TypeError as e:
            raise HandlerError("unable to perform action: %s", e)


class Status(object):

    def __init__(self, timeout=300, callback=None):
        """
        :param timeout:             seconds to wait until non activity considered stalled
        :type timeout: int          default: 300
        :param callback:            function to use for status updates
        :type callback: function    default: lambda: return acadapter('--status')
        """
        self.log = logging.getLogger(__name__ + '.Status')
        
        if not callback:
            def callback():
                return acadapter('--status')
        self._update = callback
        
        # get the initial status
        _status = self._update()
        self.activity = Activity(_status['activity'], timeout)
        self.alerts = [Alert(x) for x in _status['alerts']]
        self.busy = _status['busy']

    def __str__(self):
        return self.activity.message.decode('utf-8')

    def __unicode__(self):
        return self.activity.message

    @property
    def task(self):
        if self.activity.message:
            return self.activity.message

    @property
    def timeout(self):
        if self.activity.timeout:
            return self.activity.timeout

    @timeout.setter
    def timeout(self, t):
        self.activity.timeout = t

    @property
    def details(self):
        if self.activity.details:
            return self.activity.details

    @property
    def alert(self):
        try:
            return self.alerts[0]
        except IndexError:
            pass

    @property
    def stalled(self):
        # if self.activity == None this will trigger immediately
        return self.busy and not self.activity.active

    @property
    def progress(self):
        m = re.search(r'^Step (\d+) of (\d+)', self.activity.details)
        if m:
            v = float(m.group(1)) / int(m.group(2))
            return "{0:.0f}%".format(v * 100)

    def update(self):
        """
        Refresh the status, updating current activity and gather alerts
        if there are any alerts,
            they are passed to each handler to be processed otherwise, they are raised
            if no handlers are defined,
                the alert is raised
        
        if there are any handlers,
            pass the updated activity, alerts, and raw status to each handler
            alerts are re-raised if there is an error with any of the handlers
        
        :return: None
        """
        _status = self._update()
        self.log.debug("status: %r", _status)
        self.busy = _status['busy']
        self.alerts = [Alert(x) for x in _status['alerts']]
        
        activity = Activity(_status['activity'])
        if activity or not self.busy:
            self.activity.update(activity)
        
        self.log.debug(" activity: %s", self.activity)
        self.log.debug("   alerts: %r", self.alerts)
        self.log.debug("     busy: %s", self.busy)


def _record(path, info):
    """
    Record raw data to specified file
    :param path:    path to file
    :param info:    dict of info to record
    :return: None
    """
    logger = logging.getLogger(__name__)
    logger.debug("recording execution: %r", path)
    if not path:
        return
    
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory, 0o755)
    
    if os.path.exists(path):
        with open(path, 'a+') as f:
            f.write("{0}\n".format(info))
    else:
        with open(path, 'w+') as f:
            f.write("{0}\n".format(info))


def acadapter(command, data=None):
    logger = logging.getLogger(__name__)
    
    # build the command
    cmd = ['/usr/bin/caffeinate', '-d', '-i', '-u']
    cmd += [ACADAPTER, command]
    
    # convert python to JSON for ACAdapter.scpt
    if data:
        cmd += [json.dumps(data)]
    
    logger.debug("> {0}".format(" ".join(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    logger.debug("  OUT: %r", out)
    logger.debug("ERROR: %r", err)
    
    if log:
        # record everything to specified file (if cfgutil.log)
        try:
            _record(log, {'execution': cmd, 'output': out, 'error': err,
                          'data': data, 'command': command,
                          'returncode': p.returncode})
        except (OSError, IOError):
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


def action(choice, options=None):
    options = options or []
    args = {'choice': choice, 'options': options}
    return acadapter('--action', args)


def relaunch(force=False):
    # formatted for better readability
    scpt = ('if application "Apple Configurator 2" is running then',
            '    tell application "Apple Configurator 2" to quit',
            '    delay 1',
            'end if',
            'tell application "Apple Configurator 2" to launch')
    # join all the strings
    applscpt = "\n".join(scpt)
    if force:
        try:
            action("Cancel")
        except ACAdapterError:
            pass
    try:
        subprocess.check_call(['osascript', '-e', applscpt],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        raise Error("unable to relaunch Apple Configurator 2")


def install_vpp_apps(udids, apps, recovery=None, hook=None, **kwargs):
    if not udids:
        raise Error("no UDIDs were specified")
    elif not apps:
        raise Error("no apps were specified")
    
    logger = logging.getLogger(__name__)
    logger.info("installing VPP apps")
    logger.debug("  UDIDs: %r", udids)
    logger.debug("   APPS: %r", apps)

    try:
        status = Status(**kwargs)
    except ACAdapterError as e:
        # bug on first launch with error window
        # FIX: status should return empty dict if it wasn't running
        status = Status(**kwargs)
    # TO-DO: this is not looping correctly when:
    #       - AC is not running & has network issue
    if not status.busy:
        try:
            acadapter('--vppapps', {'udids': udids, 'apps': apps})
            logger.info("waiting for app installation to start")
            while not status.task or "apps on" not in status.task:
                status.update()
                time.sleep(1)
            logger.debug("VPP app installation started")
        except ACAdapterError:
            logger.error("failed to start VPP app installation")
            raise
    else:
        logger.info(u"AC was busy with: %s", status.task)

    try:
        step = status.details
        while status.busy:
            if step != status.details:
                step = status.details
                expiration = status.activity.expiration
                logger.info("%s: (expires: %s)", status.details, expiration)
                if hook:
                    hook(status)
            if status.alert:
                if recovery:
                    recovery(status.alert)
                else:
                    raise status.alert
            if status.stalled:
                raise ACStalled(u"stalled: %s", status.details)
            status.update()
            time.sleep(1)
        
        logger.info(u"finished %s", status)
        # clear_selection()
        logger.info("finished VPP app installation")
    
    except ACAdapterError as e:
        logger.error(u"VPP App installation failed: %s", e)
        raise
    
    except ACStalled as e:
        logger.error(u"%s stalled on %s", e, status.details)
        try:
            _status = Status(timeout=30)
            action("Cancel")
            while _status.busy:
                if _status.stalled:
                    raise ACStalled("Cancellation stalled")
                _status.update()
                time.sleep(2)
        except ACStalled as e:
            logger.error(u"couldn't cancel: %s", e)
        raise
    
    except Alert as e:
        logger.error(u"alert: %s", e)
        raise


if __name__ == '__main__':
    pass
