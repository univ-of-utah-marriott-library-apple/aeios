# -*- coding: utf-8 -*-

import os
import subprocess
import json
import stat
import inspect
import logging

'''Execute commands with `cfgutil`
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = ('Copyright (c) 2019'
                 ' University of Utah, Marriott Library')
__license__ = "MIT"
__version__ = '2.4.1'
__url__ = None
__description__ = 'Execute commands with `cfgutil`'

## CHANGELOG:
# 2.0.1:
#   - added check in Authentication to make sure permissions of the 
#     files are 0600
# 2.0.2:
#   - raise errors in the event of empty params
# 2.0.3:
#   - more error detection
# 2.0.4:
#   - modified logging
# 2.0.5:
#   - fixed bug that caused CfgutilError to overwrite Message
# 2.1.0:
#   - added Result class:
#       - homogenizes returns on many functions
#       - incorporates result, failed/missing
#       - contains reference to entire cfgutil output (for debugging)
#       - contains arguments used for execution (for debugging)
#       - contains list of ECIDs that were missing from the result
#       - failed 
#   - Changed return of most functions to incorporate Result() class
#   - modified/specialized CfgutilError Exception
#   - modified Exceptions raised
#   - no longer raises CfgutilError when TypeError, ValueError or 
#     RuntimeError are appropriate
#   - modified keyword arguments with cfgutil():
#       - returns Result() by default (was dict from json.loads())
#       - added fmt (default None):
#           - fmt='json' will return dict returned by json.loads()
#           - no other keys are supported, key may change
#       - added file (optional):
#           - specify a file where returncode, output, error, and args
#             will be written
#   - removed InstalledApps (wasn't useful enough)
#   - added TESTING flag:
#       - `import cfgutil; cfgutil.TESTING = True`
#       - if True, will not call cfgutil, but will look for 
#         kwargs['mock'] or raise RuntimeError
#       - now sort ECIDs for testing
# 2.1.1:
#   - fixed issue where _record() would raise IOError if the record
#     didn't exist
# 2.2.0:
#   - renamed CfgutilError to Error
#   - re-added CfgutilError(Error)
#   - Added FatalError(Error): raised when cfgutil exits non-zero 
#     returncode
#   - minor logging changes
#   - minor changes with Exception types
#   - modified cfgutil() to raise FatalError with non-zero returncode
#
# 2.3.0:
#   - added install_wifi_profile()
# 2.3.1:
#   - added Error.ecids property
# 2.3.2:
#   - removed Authorization()
#   - renamed CfgutilError -> Error:
#       - CfgutilError inherits from Error
#       - now CfgutilFatalError will have same functions as CfgutilError
# 2.3.3:
#   - modified list() to use Result class
#   - added documentation
#
# 2.4.0:
#   - major changes to cfgutil()
#   - built-in logging
#   - log property
#   - simplified execution
# 2.4.1:
#   - removed extra code
#   - modified errors

CFGUTILBIN = '/usr/local/bin/cfgutil'

## file to record all execution to > cfgutil.log = '/path/to/file'
log = None

## Add NullHandler to the logger (in case logging hasn't been setup)
logging.getLogger(__name__).addHandler(logging.NullHandler())


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
    '''Raised when execution of cfgutil completely fails
    '''
    pass


class AuthenticationError(Error):
    pass


class CfgutilError(Error):
    '''Raised when execution of cfgutil partially fails
    '''
    pass
    

class Result(object):
    def __init__(self, cfgout, ecids=[], err=[], cmd=[]):
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
        self.log = logging.getLogger(__name__)
        ## verify each file
        for file in (key, cert):
            self._verify(file)
        self.key = key
        self.cert = cert
    
    def _verify(self, file):
        '''verify file exists and has the correct permissions
        '''
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
        self.log.info("verified: %r", file)
    
    def args(self):
        '''returns list of arguments for cfgutil()
        '''
        return ['-C', self.cert, '-K', self.key]


def requires_authentication(subcmd):
    '''returns True if specifed subcommand requires authentication
    '''
    cmds = ['add-tags', 'activate', 'get-unlock-token',
            'install-app', 'install-profile',
            'remove-profile', 'restart', 'restore',
            'restore-backup', 'shut-down', 'wallpaper']
    if subcmd in cmds:
        return True
    else:
        return False

def _record(file, info):
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
    '''erase specified ECIDs
    '''
    if not ecids:
        raise Error('no ECIDs specified')
    return cfgutil('erase', ecids, [], auth)
    
def get(keys, ecids):
    '''get information about <keys> from specified ECIDs
    '''
    if not ecids:
        raise Error('no ECIDs specified')
    return cfgutil('get', ecids, keys)

def list(ecids=None):
    '''
    Returns list of dicts for attached devices
    
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
    '''
    _ecids = ecids if ecids else []
    result = cfgutil('list', _ecids, [])
    return [info for info in result.output.values()]

def wallpaper(ecids, image, auth, args=None):
    '''Set the wallpaper of specified ECIDs using image
    '''
    if not ecids:
        raise Error('no ECIDs specified')
    elif not image:
        raise Error('no image was specfied')

    if not args:
        args = ['--screen', 'both']
    args.append(image)

    return cfgutil('wallpaper', ecids, args, auth)

def install_wifi_profile(ecids, profile, **kwargs):
    '''install wifi profile on unmanaged devices
    NOTE:
        install-profile reports failure, but allows the wifi profile to 
        be installed regardless 
    
    Currently there is no support for checking if the wifi profile was 
    actually installed
    
    '''
    if not ecids:
        raise Error('no ECIDs specified')
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
        
def prepareDEP(ecids):
    '''prepare specified ECIDs using DEP
    '''
    if not ecids:
        raise Error('no ECIDs specified')
    args = ['--dep', '--skip-language', '--skip-region']
    return cfgutil('prepare', ecids, args)

def prepareManually(ecids):
    '''prepare devices manually
    '''
    raise NotImplementedError('prepareManually')
    if not ecids:
        raise Error('no ECIDs specified')
 
def cfgutil(command, ecids, args, auth=None):
    '''
    Executes /usr/local/bin/cfgutil with specified arguments
    returns Result() object
    '''
    logger = logging.getLogger(__name__)

    # build the command
    cmd = [CFGUTILBIN, '--format', 'JSON']

    if not command:
        err = 'no command was specfied'
        logger.error(err)
        raise Error(err)

    # list of sub-commands that require authentication
    if requires_authentication(command) or auth:
        # log.debug("auth: {0}".format(auth.args()))
        try:
            cmd += auth.args()
        except AttributeError:
            logger.error("invalid authentication: %r", auth)
            raise

    # pre-append '--ecid' per (sorted) ECID as flat list
    #   i.e. [ecid1, ecid2] -> ['--ecid', ecid1, '--ecid', ecid2]
    # and add ecids to the command
    cmd += [x for e in sorted(ecids) for x in ('--ecid', e)]

    # finally, add the command and args
    cmd += [command] + args

    logger.info("> {0}".format(" ".join(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)

    out, err = p.communicate()    
    logger.debug("    output: %r", out)
    logger.debug("     error: %r", err)
    logger.debug("returncode: %r", p.returncode)
    if log:
        # record everything to specified file (if cfgutil.log)
         _record(log, {'execution': cmd, 'output': out, 'error': err,
                       'ecids': ecids, 'args': args, 'command': command,
                       'returncode': p.returncode})
    if out:
        try:
            cfgout = json.loads(out)
            logger.debug("JSON: %r", cfgout)
        except:
            logger.exception("failed to load JSON")
            logger.debug("invalid JSON: %r", out)
            raise
    else:
        logger.debug("no JSON output returned")
        cfgout = {'Command':command, 'Type':'Error', 
                  'Message': 'output: {0!r}'.format(out),
                  'FailureReason': 'cfgutil did not return valid JSON',
                  'Output': {}, 'Detail': str(e)}

    # cfgutil command failed (action wasn't performed)
    if p.returncode != 0:
        cfgerr = err if err else "cfgutil: {0}: failed".format(command)
        raise FatalError(cfgout, cfgerr, command)

    type = cfgout.get('Type')
    if type == 'Error':
        raise CfgutilError(cfgout, 'Unknown error', command)
    elif type is None:
        raise Error(cfgout, 'unexpected output type', command)

    return Result(cfgout, ecids, cmd)

if __name__ == '__main__':
    pass
