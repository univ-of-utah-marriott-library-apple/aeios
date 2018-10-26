# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import json
import stat

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


# global reservation of <type 'list'>
_list = type([])

class Error(Exception):

    def __init__(self, err, ecids, info={}):
        self.ecids = ecids
        self.msg = err
        self.command = info.get('Command','')
        self.message = info.get('Message','')
        self.domain = info.get('Domain','')
        self.reason = info.get('FailureReason','')
        self.code = info.get('Code','')
        self.detail = info.get('Detail','')
        self.unaffected = info.get('UnaffectedDevices', [])
        self.affected = info.get('AffectedDevices', ecids)
        
    def __str__(self):
        err = "{0}: {1}".format(self.command, self.msg)
        if self.message:
            err += ": {0}".format(self.message)
        return err


class Result(object):
    '''
    '''
    def __init__(self, ecids, cfgout, _exec=[]):
        self._info = cfgout
        self._exec = _exec
        self.command = cfgout.get('Command')
        self.output = cfgout.get('Output', {})
        _type = cfgout.get('Type')
        self.ecids = cfgout.get('Devices', [])
        self.missing = [x for x in ecids if x not in self.ecids]
        # set attributes 
        if _type == 'CommandOutput':
            if self.command == 'get':
                # process get output
            else:
                # Not sure if I like: self.erase = self.ecids
                # setattr(self, self.command, self.ecids)
                pass
        elif _type == 'Error':
            # process errors
        else:
            # unknown
            pass

    def succeeded(self):
        return self.ecids

    def failed(self):
        _failed = self.missing
        # process other types of failure
        return _failed

    def info(self, ecid, key=None):
        '''potential to be amazingly helpful or a pain in the ass
        '''
        # result.info() -> all of everything?
        # result.info(ecid) -> info for just ecid?
        # result.info(ecids) -> info for all specified ecids?
        # result.info(ecids, keys) -> info for specified ecids and keys
        pass
        
    def get(self, ecids, keys):
        # result.get(ecid)
        pass
        

class CfgutilError(Error):

    def __init__(self, message, ecids, info={}):
        self.ecids = ecids
        self.msg = message
        self.command = info.get('Command','')
        self.message = info.get('Message','')
        self.domain = info.get('Domain','')
        self.reason = info.get('FailureReason','')
        self.code = info.get('Code','')
        self.detail = info.get('Detail','')
        self.unaffected = info.get('UnaffectedDevices', [])
        self.affected = info.get('AffectedDevices', ecids)
        
    def __str__(self):
        err = "{0}: {1}".format(self.command, self.msg)
        if self.message:
            err += ": {0}".format(self.message)
        return err


class Authentication(object):

    def __init__(self, cert, pkey, log=None):
        if not log:
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
                os.chmod(file, 0600)
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

def erase(ecids, **kwargs):
    if not ecids:
        _info = {'Command': 'erase',
                 'Detail': 'invalid use of cfgutil.erase()'}
        raise CfgutilError('no ecids were specfied', [], _info)
    cfgout = cfgutil('erase', ecids, **kwargs)
    _succeeded = cfgout.get('Devices', [])
    missing = [x for x in ecids if x not in _succeeded]
    return _succeeded, missing

def installedApps(ecids, **kwargs):
    if not ecids:
        _info = {'Command': 'get installedApps',
                 'Detail': 'invalid use of cfgutil.installedApps()'}
        raise CfgutilError('no ecids were specfied', [], _info)
    cfgoutput = get(['installedApps'], ecids, **kwargs)
    installed = {}
    for ecid,v in cfgoutput.items():
        installed[ecid] = []
        for app in v['installedApps']:
            installed[ecid].append(app['displayName'])
    return installed
    
def get(keys, ecids=[], **kwargs):
    '''get specified key(s) from cfgutil()
    '''
    if not isinstance(keys, (_list, set)):
        raise TypeError("not list or set: {0}".format(keys))
    _info = {'Command': 'get', 
             'Detail': 'invalid use of cfgutil.get()'}
    if not keys:
        raise CfgutilError('no keys were specfied', ecids, _info)
    elif not ecids:
        raise CfgutilError('no ecids were specfied', [], _info)

    if not isinstance(keys, (type([]),set)):
        raise TypeError("not list or set: {0}".format(keys))

    cfgout = cfgutil('get', ecids, args=keys, **kwargs)

    _succeeded = cfgout.get('Devices', [])
    missing = [x for x in ecids if x not in _succeeded]

    info = {}
    for ecid in ecids:
        device = cfgout['Output'].get(ecid, {})
        info[ecid] = {}
        for key in keys:
            info[ecid][key] = device.get(key)

    #TO-DO: figure out failure
    failed = {}
    return info, failed, missing

def list(*args, **kwargs):
    '''Returns list of attached devices
    '''
    cfginfo = cfgutil('list', **kwargs)
    devices = []
    for device in cfginfo['Output'].values():
        devices.append(device)
    return devices

def wallpaper(ecids, image, args, auth, **kwargs):
    _info = {'Command': 'wallpaper', 
             'Detail': 'invalid use of cfgutil.wallpaper()'}
    if not ecids:
        raise CfgutilError('no ecids were specfied', [], _info)
    elif not image:
        raise CfgutilError('no image was specfied', ecids, _info)

    if not args:
        args = ['--screen', 'both']
    args.append(image)
    cfgout = cfgutil('wallpaper', ecids, args, auth, **kwargs)
    _succeeded = cfgout.get('Devices', [])
    missing = [x for x in ecids if x not in _succeeded]
    return _succeeded, missing
        
def prepareDEP(ecids, **kwargs):
    '''prepare devices using DEP
    '''
    if not ecids:
        _info = {'Command': 'prepare', 
                 'Detail': 'invalid use of cfgutil.prepareDEP()'}
        raise CfgutilError('no ecids were specfied', [], _info)
    args = ['--dep', '--skip-language', '--skip-region']
    cfgout = cfgutil('prepare', ecids, args=args)
    _succeeded = cfgout.get('Devices', [])
    missing = [x for x in ecids if x not in _succeeded]
    return _succeeded, missing

def prepareManually(ecids, **kwargs):
    '''prepare devices manually
    '''
    _info = {'Command': 'prepare', 
             'Detail': 'invalid use of cfgutil.prepareManually()'}
    if not ecids:
        raise CfgutilError('no ecids were specfied', [], _info)
    raise NotImplementedError('prepareManually')
 
def cfgutil(command, ecids=[], args=[], auth=None, 
                             timeout=None, log=None):
    '''Executes /usr/local/bin/cfgutil with specified arguments
    returns output in JSON
    '''
    _cfginfo = {'Command':command}
    if not log:
        log = logging.getLogger(__name__)
        log.addHandler(logging.NullHandler())

    if not command:
        import inspect
        caller = inspect.stack()[1][3]
        _info = {'Command': 'UNKNOWN', 
                 'Detail': 'called by: {0}'.format(caller),
                 'Code': 102 } # errno.ED /* ? */
        raise CfgutilError('command missing', ecids, _info)

    cfgutilbin = '/usr/local/bin/cfgutil'

    # can't run cfgutil if it doesn't exist (or if broken symlink)
    if not os.path.exists(cfgutilbin):
        err = "executable missing: {0}".format(cfgutilbin)
        raise CfgutilError(err, ecids, _cfginfo)

    # pre-append '--ecid' per specified ECID as flat list
    #   [ecid1, ecid2] -> ['--ecid', ecid1, '--ecid', ecid2]
    ecidargs = [x for e in ecids for x in ('--ecid', e)]

    # build the command
    cmd = [cfgutilbin, '--format', 'JSON']

    # add timeout (if one)
    if timeout:
        cmd += ['--timeout', str(timeout)]

    # list of sub-commands that require authentication
    if requires_authentication(command) or auth:
        # log.debug("auth: {0}".format(auth.args()))
        try:
            cmd += auth.args()
        except AttributeError:
            err = "invalid authentication: {0}".format(auth)
            raise CfgutilError(err, ecids, _cfginfo)
        
    # add the targeted ECIDs, command, and args
    cmd += ecidargs + [command] + args
    
    log.debug("> {0}".format(" ".join(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    out, err = p.communicate()
    try:
        cfgout = json.loads(out)
    except:
        cfgout = _cfginfo

    if p.returncode != 0:
        cfgerr = "cfgutil: {0}: failed".format(command)
        if err:
            cfgerrs = [x for x in err.splitlines() if x]
            cfgerr = cfgout.get('Message', cfgerrs[-1])
        if not out:
            log.debug("cfgutil: {0}: missing output".format(command))
        else:
            log.debug("cfgutil: error: {0}".format(cfgout))
        raise CfgutilError(cfgerr, ecids, cfgout)

    type = cfgout.get('Type')
    if type == 'Error':
        cfgerr = cfgout.get('Message', 'Unknown Error')
        raise CfutilError(cfgerr, ecids, cfgout)
    elif type is None:
        cfgerr = cfgout.get('Message', 'Unknown Error')
        raise CfutilError(cfgerr, ecids, cfgout)

    log.debug("cfgutil: output: {0}".format(cfgout))
    return cfgout

if __name__ == '__main__':
    pass
