# -*- coding: utf-8 -*-

import os
import subprocess
import json
import stat
import inspect

'''Execute commands with `cfgutil`
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '2.0.5'
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

TESTING = False
CFGUTILBIN = '/usr/local/bin/cfgutil'
# this library is useless without cfgutil, so let's error very quickly
# not sure if thise is ideal, or if I should raise warning or what
# if not os.path.exists(CFGUTILBIN):
#     err = "{0}: missing executable".format(CFGUTILBIN)
#     raise RuntimeError(err)


class Error(Exception):
    pass


class CfgutilError(Error):

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


class Result(object):
    def __init__(self, cfgout, ecids=[], err=[], cmd=[]):
        self._output = cfgout
        self.cmdargs = cmd
        # self._type = cfgout.get('Type', '')
        self.command = cfgout.get('Command', '')
        self.ecids = cfgout.get('Devices', [])
        self.output = cfgout.get('Output', {})
        self.missing = [x for x in ecids if x not in self.ecids]

    def get(self, ecid, default=None):
        return self.output.get(ecid, default)


class Authentication(object):

    def __init__(self, cert, pkey, log=None):
        if not log:
            import logging
            self.log = logging.getLogger(__name__)
            self.log.addHandler(logging.NullHandler())
        for file in [cert, pkey]:
            if not os.path.exists(file):
                err = "missing file: {0}".format(file)
                log.error(err)
                raise CfgutilError(err, ecids=[])
            ## check file mode
            st_mode = os.stat(file).st_mode
            ## stat.S_IREAD|stat.S_IWRITE == 0600 (-rw-------)
            o_rw = stat.S_IREAD | stat.S_IWRITE
            if stat.S_IMODE(st_mode) != o_rw:
                os.chmod(file, 0o0600)
        self.cert = cert
        self.key = pkey
    
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
    with open(file, 'a+') as f:
        f.write("{0}\n".format(info))

def erase(ecids, **kwargs):
    '''erase specified ECIDs
    '''
    if not ecids:
        raise ValueError('no ECIDs specified')
    return cfgutil('erase', ecids, **kwargs)
    
def get(keys, ecids, **kwargs):
    '''get information about <keys> from specified ECIDs
    '''
    if not ecids:
        raise ValueError('no ECIDs specified')
    if not keys:
        keys = ['all']
    return cfgutil('get', ecids, args=keys, **kwargs)

def list(*args, **kwargs):
    '''Returns list of attached devices
    '''
    output = cfgutil('list', *args, fmt='json', **kwargs)
    return [info for info in output['Output'].values()]

def wallpaper(ecids, image, args, auth, **kwargs):
    '''Set the wallpaper of specified ECIDs using image
    '''
    if not ecids:
        raise ValueError('no ECIDs specified')
    elif not image:
        raise ValueError('no image was specfied')

    if not args:
        args = ['--screen', 'both']
    args.append(image)

    return cfgutil('wallpaper', ecids, args, auth, **kwargs)
        
def prepareDEP(ecids, **kwargs):
    '''prepare specified ECIDs using DEP
    '''
    if not ecids:
        raise ValueError('no ECIDs specified')
    args = ['--dep', '--skip-language', '--skip-region']
    return cfgutil('prepare', ecids, args, **kwargs)

def prepareManually(ecids, **kwargs):
    '''prepare devices manually
    '''
    if not ecids:
        raise ValueError('no ECIDs specified')
    raise NotImplementedError('prepareManually')
 
def cfgutil(command, ecids=[], args=[], auth=None, log=None, 
            file=None, fmt=None, **kwargs):
    '''Executes /usr/local/bin/cfgutil with specified arguments
    returns output in JSON
    '''
    if not log:
        import logging
        log = logging.getLogger(__name__)
        log.addHandler(logging.NullHandler())

    # build the command
    cmd = [CFGUTILBIN, '--format', 'JSON']

    if not command:
        err = 'cfgutil: no command was specfied'
        log.error(err)
        raise RuntimeError(err)

    # list of sub-commands that require authentication
    if requires_authentication(command) or auth:
        # log.debug("auth: {0}".format(auth.args()))
        try:
            cmd += auth.args()
        except AttributeError:
            log.error("invalid authentication: {0}".format(auth))
            raise

    # pre-append '--ecid' per specified ECID as flat list
    #   [ecid1, ecid2] -> ['--ecid', ecid1, '--ecid', ecid2]
    # sorted for comparison in TESTING
    ecidargs = [x for e in sorted(ecids) for x in ('--ecid', e)]

    # add the targeted ECIDs, command, and args
    cmd += ecidargs + [command] + args
    
    log.debug("> {0}".format(" ".join(cmd)))
    if not TESTING:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
        out, err = p.communicate()    
        if file:
            # record everything to specified file
            _info = {'execution': cmd, 'output': out, 'error': err,
                     'ecids': ecids, 'args': args, 'command': command,
                     'returncode': p.returncode}
            _record(file, _info)
    else:
        try:
            _mock = kwargs['mock']
            out, err = _mock['output'], _mock['error']
            p = object()
            p.returncode = _mock['returncode']
            if _mock['execution'] != cmd:
                log.error("execution flags did not match")
                log.debug("command args: {0}".format(cmd))
                log.debug("expected: {0}".format(_mock['execution']))
                raise Error("execution flags did not match")
        except KeyError:
            log.error("no mock data provided for testing")
            raise RuntimeError("no data to test")

    try:
        cfgout = json.loads(out)
        log.debug("cfgutil: output: {0}".format(cfgout))
    except Exception as e:
        # TO-DO: need to test failed commands
        log.error("cfgutil: couldn't load output")
        cfgout = {'Command':command, 'Type':'Error', 
                  'Message': 'no output was returned',
                  'FailureReason': 'cfgutil did not return valid JSON',
                  'Output': {}, 'Detail': str(e)}

    # pseudo-reverse-compatibility (mostly for cfgutil.list())
    if fmt and fmt.lower() == 'json':
        return cfgout

    # cfgutil command failed (action wasn't performed)
    if p.returncode != 0:
        cfgerr = "cfgutil: {0}: failed".format(command)
        if err:
            cfgerrs = [x for x in err.splitlines() if x]
            cfgerr = cfgout.get('Message', cfgerrs[-1])
        raise CfgutilError(cfgout, cfgerr, command)

    type = cfgout.get('Type')
    if type == 'Error':
        raise CfutilError(cfgout, 'Unknown error', command)
    elif type is None:
        raise CfutilError(cfgout, 'missing output type', command)

    return Result(cfgout, ecids, cmd)

if __name__ == '__main__':
    pass
