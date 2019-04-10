# -*- coding: utf-8 -*-

import os
import subprocess
import json
import stat
import inspect
import logging

"""
Execute commands with `cfgutil`
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "2.5.0"

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

CFGUTILBIN = '/usr/local/bin/cfgutil'

# record raw execution info (cfgutil.log = '/path/to/execution.log')
log = None

# TO-DO: this was a mistake (I need to move this all to CfgutilError)
class Error(Exception):

    def __init__(self, info, msg='', cmd=None):
        if not cmd:
            cmd = inspect.stack()[1][3]
        self.command = info.get('Command', cmd)
        self.message = info.get('Message', msg)
        self.code = info.get('Code', 61) # ENODATA: 'No data available'
        self.domain = info.get('Domain', '')
        self.reason = info.get('FailureReason', '')
        self.detail = info.get('Detail', '')
        self.affected = info.get('AffectedDevices', [])
        self.unaffected = info.get('UnaffectedDevices', [])
        self.ecids = self.affected + self.unaffected

    def __str__(self):
        # ["<cmd>: "] + "<msg> (<code>)" + [": devices: <affected>"]
        _str = "{0} ({1})".format(self.message, self.code)
        if self.command:
            _str = "{0}: {1}".format(self.command, _str)
        if self.affected:
            _str += ": devices: {0}".format(self.affected)
        return _str

    def __repr__(self):
        # include attributes with values
        _repr = '<{0}.{1} object at 0x{2:x} {3}>'
        _dict = {k:v for k,v in self.__dict__.items() if v}
        return _repr.format(__name__, 'Error', id(self), _dict)


class FatalError(Error):
    """
    Raised when execution of cfgutil completely fails
    """
    pass


class AuthenticationError(Exception):
    """
    Raised when incorrect Authentication was provided
    OR when Authentication required and None or incorrect
    """
    pass


class CfgutilError(Error):
    '''Raised when execution of cfgutil partially fails
    '''
    pass
    

class Result(object):
    def __init__(self, cfgout, ecids=(), err=(), cmd=()):
        self._output = cfgout
        self.cmdargs = cmd
        self.command = cfgout.get('Command', '')
        self.ecids = cfgout.get('Devices', [])
        self.output = cfgout.get('Output', {})
        self.missing = [x for x in ecids if x not in self.ecids]

    def get(self, ecid, default=None):
        return self.output.get(ecid, default)


class Authentication(object):

    def __init__(self, key, cert):
        self.log = logging.getLogger(__name__ + '.Authentication')
        ## verify each file
        for file in (key, cert):
            self._verify(file)
        self.key = key
        self.cert = cert
    
    def _verify(self, file):
        """
        verify file exists and has the correct permissions
        """
        self.log.debug("verifying: %r", file)
        if not os.path.exists(file):
            self.log.error("no such file: %r", file)
            raise AuthenticationError(e)
        ## check file permissions are 0600 ~ '-rw-------'
        mode = stat.S_IMODE(os.stat(file).st_mode)
        if mode != (stat.S_IREAD|stat.S_IWRITE):
            e = "invalid permissions: {0:04do}: {1}".format(mode, file)
            self.log.error(e)
            raise AuthenticationError(e)
        self.log.debug("verified: %r", file)
    
    def args(self):
        """
        :return: list of arguments for cfgutil()
        """
        return ['-C', self.cert, '-K', self.key]


def requires_authentication(subcmd):
    """
    :return: True if specifed subcommand requires authentication
    """
    cmds = ['add-tags', 'activate', 'get-unlock-token',
            'install-app', 'install-profile',
            'remove-profile', 'restart', 'restore',
            'restore-backup', 'shut-down', 'wallpaper']
    if subcmd in cmds:
        return True
    else:
        return False


def _record(file, info):
    """
    Record raw data to specified file

    :param path:    path to file
    :param info:    dict of info to record
    :return: None
    """
    logger = logging.getLogger(__name__)
    logger.debug("recording execution to: %r", file)

    if not os.path.exists(file):
        try:
            dir = os.path.dirname(file)
            os.makedirs(os.path.dirname(file))
        except OSError as e:
            if e.errno != 17 or not os.path.isdir(dir):
                logger.error(e)
                raise e
        with open(file, 'w+') as f:
            f.write("{0}\n".format(info))
    else:
        with open(file, 'a+') as f:
            f.write("{0}\n".format(info))

    
def erase(ecids, auth=None):
    """
    Erase devices

    :param ecids:   iterable of ECIDs
    :param auth:    Authentication object
    :returns:       cfgutil.Result
    """
    if not ecids:
        raise ValueError('no ECIDs specified')
    return cfgutil('erase', ecids, [], auth)


def get(keys, ecids):
    """
    Get information about <keys> from specified ECIDs

    :param keys:    list of property keys supported by `cfgutil`
    :param ecids:   list of ECIDs
    :returns:       cfgutil.Result
    """
    if not ecids:
        raise ValueError('no ECIDs specified')
    return cfgutil('get', ecids, keys)


# TO-DO: this should be changed to list_devices
def list(ecids=None):
    """
    Get connected devices
    
    :returns:    list of dicts for attached devices
    
    Each dict will have the following keys defined:
        UDID, ECID, name, deviceType, locationID
    
    e.g.:
    >>> cfgutil.list()
    [{'ECID': '0x123456789ABCD0',
      'UDID': 'a0111222333444555666777888999abcdefabcde',
      'deviceType': 'iPad7,5',
      'locationID': 337920512,
      'name': 'checkout-ipad-1'},
     {'ECID': '0x123456789ABCD1',
      'UDID': 'a1111222333444555666777888999abcdefabcde',
      'deviceType': 'iPad8,1',
      'locationID': 337907712,
      'name': 'checkout-ipad-2'}, ...]
    """
    _ecids = ecids if ecids else []
    result = cfgutil('list', _ecids, [])
    return [info for info in result.output.values()]


def wallpaper(ecids, image, auth, args=None):
    """
    Set the wallpaper of specified ECIDs using image

    :param ecids:   list of ECIDs
    :param image:   path to image
    :param auth:    cfgutil.Authentication
    :param args:    list of additional arguments for `cfgutil`
    :returns:        cfgutil.Result
    """
    if not ecids:
        raise ValueError('no ECIDs specified')
    elif not image:
        raise ValueError('no image was specfied')

    if not args:
        args = ['--screen', 'both']
    args.append(image)

    return cfgutil('wallpaper', ecids, args, auth)


def install_wifi_profile(ecids, profile):
    """
    Install wifi profile on unmanaged devices

    :param ecids:       list of ecids
    :param profile:     path to wifi profile
    :returns:           None

    NOTE:
        install-profile reports failure, but allows the wifi profile to 
        be installed regardless 
    
        Currently there is no support for checking if the wifi profile was 
        actually installed
    """
    if not ecids:
        raise ValueError('no ECIDs specified')
    if not os.path.exists(profile):
        raise Error("profile missing: {0}".format(profile))

    # dummy auth (not required for a unmanaged device wifi profile)
    class _faux(object):
        def args(self):
            return []
    try:
        # incorrectly reports failure 
        cfgutil('install-profile', ecids, [profile], _faux())
    except:
        pass


def restart(ecids, auth):
    if not ecids:
        raise ValueError('no ECIDs specified')
    return cfgutil('restart', ecids, [], auth)


def shutdown(ecids, auth):
    if not ecids:
        raise ValueError('no ECIDs specified')
    return cfgutil('shut-down', ecids, [], auth)


# TO-DO: combine prepareManually and prepareDEP to prepare()
# def prepare(ecids, args=None):
#     if not ecids:
#         raise ValueError('no ECIDs specified')
#     if not args:
#         args = ['--dep', '--skip-language', '--skip-region']
#      return cfgutil('prepare', ecids, args)

# TO-DO: remove (see prepare above)
def prepareDEP(ecids):
    """
    Prepare devices using DEP
    """
    if not ecids:
        raise ValueError('no ECIDs specified')
    args = ['--dep', '--skip-language', '--skip-region']
    return cfgutil('prepare', ecids, args)


# TO-DO: remove (see prepare above)
def prepareManually(ecids):
    """
    Prepare devices manually (Not Implemented)
    """
    raise NotImplementedError('prepareManually')
    if not ecids:
        raise ValueError('no ECIDs specified')


def cfgutil(command, ecids, args, auth=None):
    """
    Executes `cfgutil` with specified arguments

    :param command:     command to execute
    :param ecids:       list of device ECIDs
    :param args:        list of additional arguments for `cfgutil`
    :param auth:        cfgutil.Authentication     

    :return:    cfgutil.Result

    :raises:    cfgutil.AuthenticationError when command requires authorization
                    but None, or invalid authentication provided
    :raises:    cfgutil.FatalError on non-zero status (nothing was modified)
    :raises:    cfgutil.CfgutilError some modification (but not all)
    """
    logger = logging.getLogger(__name__)

    # build the command
    cmd = [CFGUTILBIN, '--format', 'JSON']

    if not command:
        raise ValueError('no command was specified')

    # list of sub-commands that require authentication
    if requires_authentication(command) or auth:
        try:
            cmd += auth.args()
        except AttributeError:
            logger.error("invalid authentication: %r", auth)
            raise

    # pre-append '--ecid' per (sorted) ECID as flat list
    # i.e. [ecid1, ecid2] -> ['--ecid', ecid1, '--ecid', ecid2]
    cmd += [x for e in sorted(ecids) for x in ('--ecid', e)]

    # finally, add the command and args
    cmd += [command] + args

    logger.info("> {0}".format(" ".join(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()    

    logger.debug("    output: %r", out)
    logger.debug("     error: %r", err)
    logger.debug("returncode: %r", p.returncode)

    if log:
        # record everything to specified file (if cfgutil.log)
        try:
            _record(log, {'execution': cmd, 'output': out, 'error': err,
                          'ecids': ecids, 'args': args, 'command': command,
                          'returncode': p.returncode})
        except:
            logger.debug("failed to record execution data")

    if out:
        try:
            cfgout = json.loads(out)
        except:
            logger.error("%s: returned invalid JSON: %r", command, out)
            raise
    else:
        logger.debug("no JSON output returned")
        cfgout = {'Command': command, 'Type': 'Error', 
                  'Message': err, 'Details': u"ERR: {0!r}".format(err),
                  'FailureReason': 'missing output', 'Output': {}}

    # cfgutil command failed (action wasn't performed)
    if p.returncode != 0:
        cfgerr = err if err else "cfgutil: {0}: failed".format(command)
        raise FatalError(cfgout, cfgerr, command)

    _type = cfgout.get('Type')
    if _type == 'Error':
        raise CfgutilError(cfgout, 'Unknown error', command)
    elif _type is None:
        # TO-DO: remove (this shouldn't happen ever)
        raise Error(cfgout, 'unexpected output type', command)

    return Result(cfgout, ecids, cmd)


if __name__ == '__main__':
    pass
