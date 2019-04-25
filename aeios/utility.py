# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
import logging
import logging.config
import argparse
import subprocess

from . import resources
from . import config

"""
Utility functions for aeios
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "2.0.0"

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

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


class Error(Exception):
    """
    Base Exception
    """
    pass


class Parser(object):
    """
    Class for organizing arparse.ArgumentParser namespace
    """
    def __init__(self):
        self.parser = argparse.ArgumentParser(description='configures aeios')
        self.parser.add_argument('-v', '--verbose', action='store_true', 
                                 help='be verbose')
        self.parser.add_argument('-d', '--debug', action='store_true',
                                 help='be VERY verbose')
        self.parser.add_argument('--version', action='store_true', 
                                 help='print version and exit')

        desc = 'see `%(prog)s COMMAND --help` for more information'
        self.subparsers = self.parser.add_subparsers(title='COMMANDS', 
                                                     dest='cmd', 
                                                     description=desc)
        # aeiosutil start [--login]
        # Namespace(cmd='start', login=False)
        start = self.subparsers.add_parser('start', help='start automation',
                                          description="start automation")
        start.add_argument('--login', action='store_false', default=None,
                           help='enable auto-starting at login')

        # aeiosutil stop [--login]
        # Namespace(cmd='stop', login=False)
        stop = self.subparsers.add_parser('stop', help='stop automation',
                                          description="stop automation")
        stop.add_argument('--login', action='store_true', default=None,
                          help='disable auto-starting at login')
                                          
        self.add()
        self.remove()
        self.reset()
        # self.info()
        # self.list()
        self.configure()

    def add(self):
        """
        add parsers for `aeiosutil add`
            app APP
            identity (--p12 | --certs) PATH
            image (--background | --alert | --lock ) PATH
            wifi PATH
        """
        desc = "add various compontents to automation"
        p = self.subparsers.add_parser('add', help='add to aeios', 
                                       description=desc)

        desc = 'see `%(prog)s ITEM --help` for more information'
        sp = p.add_subparsers(title='ITEMS', dest='item', description=desc)

        # aeiosutil add app APP
        # Namespace(cmd='add', item='app', name=<NAME>)
        app = sp.add_parser('app', help='add apps', 
                            description='automate app installation')
        app.add_argument('name', metavar='APP', 
                         help='iTunes name (as seen in Apple Configurator 2)')

        # (NOT YET SUPPORTED)
        # add app [--group GROUP] APP 
        # app.add_argument('--group', 
        #                  help='only install app on devices in GROUP')

        # add identity (--p12 | --certs) PATH 
        # Namespace(cmd='add', item='identity', p12=<True|False>, path=<PATH>)
        identity = sp.add_parser('identity', help='add supervision identity',
                                 description='add supervision identity')
        identity.add_argument('path', help='path to identity')
    
        # mutually exclusive (required): (--p12 | --certs)
        id_group = identity.add_mutually_exclusive_group(required=True)
        id_group.add_argument('--p12', action='store_true', dest='p12',
                              help='convert pkcs12 file, and import certs')
        id_group.add_argument('--certs', action='store_false', dest='p12',
                              help='import certs from PATH')

        # add image (--background | --alert | --lock) PATH 
        # Namespace(cmd='add', item='image', image=<background|lock|alert>, 
        #           path=<PATH>)
        img = sp.add_parser('image', help='add image',
                            description='set custom background images')
        img.add_argument('path', metavar='PATH', help='path to image')
    
        # mutually exclusive (required): (--background | --alert | --lock)
        img_group = img.add_mutually_exclusive_group(required=True)
        img_group.add_argument('--background', action='store_const', 
                               dest='image', const='background',
                               help='use as background image')
        img_group.add_argument('--alert', action='store_const', 
                               dest='image', const='alert',
                               help='use as alert image')
        img_group.add_argument('--lock', action='store_const', 
                               dest='image', const='lock',
                               help='use as lock image')

        # (NOT YET SUPPORTED)
        # add profile [--wifi] PATH
        # profile = sp.add_parser('profile', help='add profile',
        #                         description='add profile to automation')
        # profile.add_argument('path', metavar='PATH', 
        #                      help='path of mobile config profile')
        # profile.add_argument('--wifi', action='store_true', 
        #                      help='use profile for connecting to wifi')

        # add wifi PATH
        # Namespace(cmd='add', item='wifi', path=<PATH>)
        wifi = sp.add_parser('wifi',  help='add Wi-Fi profile',
                             description='Wi-Fi profile for DEP enrollment')
        wifi.add_argument('path', metavar='PATH', 
                          help='path to wifi.mobileconfig file')

    def remove(self):
        """
        Add parsers for `remove` subcommand
            app NAME
            identity
            image (--background | --lock | --alert)
            wifi
        """
        desc = "remove various compontents from automation"
        p = self.subparsers.add_parser('remove', help='remove from aeios',
                                      description=desc)
        desc = 'see `%(prog)s ITEM --help` for more information'
        sp = p.add_subparsers(title='ITEMS', dest='item', description=desc)
        
        # aeiosutil remove app APP
        # Namespace(cmd='remove', item='app', name=<NAME>)
        app = sp.add_parser('app', help='remove apps',
                            description='remove apps from automation')
        
        app.add_argument('name', metavar='APP', 
                         help='iTunes name of APP (as seen in VPP)')

        # aeiosutil remove identity
        # Namespace(cmd='remove', item='identity')
        _id = sp.add_parser('identity', help='remove supervision identity',
                            description='remove supervision identity files')

        # aeiosutil remove image (--background | --alert | --lock | --all)
        # Namespace(cmd='remove', item='image', image=<background|alert|lock>)
        img = sp.add_parser('image', help='remove images',
                            description='remove images from aeios')
        img_group = img.add_mutually_exclusive_group(required=True)
        img_group.add_argument('--background', action='store_const', 
                               dest='image', const='background',
                               help='remove background image')
        img_group.add_argument('--alert', action='store_const', 
                               dest='image', const='alert',
                               help='remove alert image')
        img_group.add_argument('--lock', action='store_const', 
                               dest='image', const='lock',
                               help='remove lock image')
        img_group.add_argument('--all', action='store_const', 
                               dest='image', const='all',
                               help='remove all images')

        # aeiosutil remove wifi
        # Namespace(cmd='remove', item='wifi')
        wifi = sp.add_parser('wifi',  help='remove Wi-Fi profile',
                             description='Wi-Fi profile for DEP enrollment')

        # aeiosutil remove reporting
        # Namespace(cmd='remove', item='reporting')
        report = sp.add_parser('reporting', help='reset reporting',
                               description='Configuration for reporting')

    def info(self):
        pass

    def list(self):
        pass

    def configure(self):
        # configure slack [--name NAME] URL channel
        desc = "remove various compontents from automation"
        p = self.subparsers.add_parser('configure', help='configure aeios',
                                      description=desc)
        desc = 'see `%(prog)s ITEM --help` for more information'
        sp = p.add_subparsers(title='ITEMS', dest='item', description=desc)

        # aeiosutil configure slack [--name NAME] URL CHANNEL
        # Namespace(cmd='configure', item='slack', URL=<URL>, 
        #           channel=<CHANNEL>, name=<aeios|NAME>)
        slack = sp.add_parser('slack', help='configure slack', 
                              description='configure slack reporting settings')

        slack.add_argument('URL', help='slack url')
        slack.add_argument('channel', help='slack channel')
        slack.add_argument('--name', default='aeios',
                           help='name of the reporter')

        # aeiosutil configure idle SECONDS
        # Namespace(cmd='configure', item='idle', seconds=<SECONDS>)
        idle = sp.add_parser('idle', help='configure idle timer', 
                              description='configure time between idle runs')
        idle.add_argument('seconds', metavar='SECONDS',
                          help='time (in seconds) between idle run')
        
    def reset(self):
        # reset [--force]
        desc = "reset various components of aeios"
        p = self.subparsers.add_parser('reset', help='reset aeios',
                                       description=desc)
        desc = 'see `%(prog)s ITEM --help` for more information'
        sp = p.add_subparsers(title='ITEMS', dest='item', description=desc)

        # aeiosutil reset ignored
        # Namespace(cmd='reset', item='ignored')
        ignored = sp.add_parser('ignored', help='reset ignored devices', 
                                description='reset ignored devices')

        # aeiosutil reset ignored
        # Namespace(cmd='reset', item='tasks')
        tasks = sp.add_parser('tasks', help='reset queued tasks', 
                              description='reset queued tasks')
        
    def parse(self, argv):
        """
        :param argv: list of arguments to parse
        :return: 
        """
        return self.parser.parse_args(argv)


# FUNCTIONS
def launchagent(disabled=None):
    '''
    takes enabled and modifies key, based on value
    creates LaunchAgent (if it doesn't already exist)
    :return: full path
    
    '''
    logger = logging.getLogger(__name__)
    label = resources.DOMAIN + '.aeios'
    useragents = os.path.expanduser('~/Library/LaunchAgents')
    conf = config.Manager(label, path=useragents)

    # create (if missing)
    if not os.path.exists(conf.file):
        default = {'Disabled': True if disabled is None else disabled,
                   'LimitLoadToSessionType': ['Aqua'],
                   'KeepAlive': True,
                   'Label': label,
                   # 'Program': '/usr/local/bin/aeiosutil',
                   # 'ProgramArguments': ['aeiosutil', 'daemon']}
                   'Program': '/usr/local/bin/checkout_ipads.py',
                   'ProgramArguments': ['checkout_ipads.py']}
        logger.debug("writing defaults: %r", default)
        conf.write(default)
    elif disabled is not None:
        data = {'Disabled': disabled}
        logger.debug("updating LaunchAgent: %r", data)
        conf.update(data)

    return conf.file


def start(onlogin):
    logger = logging.getLogger(__name__)
    cmd = ['launchctl', 'load', '-F', launchagent(disabled=onlogin)]
    subprocess.check_call(cmd, stdout=subprocess.PIPE)


def stop(onlogin):
    logger = logging.getLogger(__name__)
    cmd = ['launchctl', 'unload', '-F', launchagent(disabled=onlogin)]
    subprocess.check_call(cmd, stdout=subprocess.PIPE)
    
    
def add_item(path, dir, name=None):
    logger = logging.getLogger(__name__)
    if not name:
        dst = os.path.join(dir, os.path.basename(path))
    else:
        ext = os.path.splitext(path)[1]
        dst = os.path.join(dir, name + ext)
    logger.info("adding: %r", path)
    logger.debug("> copyfile: %r -> %r", path, dst)
    shutil.copyfile(path, dst)
    

def add_wifi_profile(path, dest):
    logger = logging.getLogger(__name__)
    logger.debug("> copyfile: %r -> %r", path, dest)
    shutil.copyfile(path, dest)
    logger.info("added Wi-Fi profile: %r", path)


def _hide_pass(cmd):
    _hidden = [re.sub(r'^pass:.+$', 'pass:******', x) for x in cmd]
    return " ".join(_hidden)


def convert_p12(p12, dir, passwd, name='identity'):
    logger = logging.getLogger(__name__)
    _conversion = {'der': (['-nodes', '-nocerts'],'rsa'),
                   'crt': (['-nokeys', '-clcerts'],'x509')}
    _passwd = 'pass:{0}'.format(passwd)

    pkcs = ['openssl', 'pkcs12', '-in', p12, '-passin', _passwd]

    for ext,args in _conversion.items():
        file = os.path.join(dir, "{0}.{1}".format(name, ext))
        _convert = ['openssl', args[1], '-outform', 'DER', '-out', file]

        logger.debug("> %s", _hide_pass(pkcs + args[0] + ['|'] + _convert))
        p = subprocess.Popen(pkcs + args[0], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        c = subprocess.Popen(_convert, stdin=p.stdout, stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
        out, err = c.communicate()
        if c.returncode != 0:
            e = "unable to convert pem to der: {0}".format(err)
            logger.error(e)
            raise RuntimeError(e)
        # convert file permissions 
        logger.debug("> chmod: %o: %r", 0o0600, file)
        os.chmod(file, 0o0600)


def copy_certs(path):
    """
    :path:  directory containing exported supervision identity key and cert
    """
    logger = logging.getLogger(__name__)
    
    logger.debug("locating identity files: %r", path)
    if not os.path.isdir(path):
        err = "invalid directory: {0!r}".format(path)
        logger.error(err)
        raise ValueError(err)

    resource = resources.Resources()
    key, cert = None, None
    for root, _, files in os.walk(path):
        for name in files:
            ext = os.path.splitext(name)[1]
            _path = os.path.join(root, name)
            if ext in ('.der', '.key'):
                logger.debug("found key: %r", name)
                if key:
                    raise ValueError("multiple private keys found")
                key = (_path, resource.key)
            elif ext in ('.cert', '.crt'):
                logger.debug("found cert: %r", name)
                if cert:
                    raise ValueError("multiple certs found")
                cert = (_path, resource.cert)
            else:
                logger.debug("skipping: %r", name)
                continue

    if not cert:
        raise ValueError("missing cert")
    elif not key:
        raise ValueError("missing private key")
    
    # iterate (cert, key) as tuples (<src>, <dst>)
    for src, dst in (cert, key):
        logger.debug("> copyfile: %r -> %r", src, dst)
        shutil.copyfile(src, dst)
        logger.debug("> chmod: %o: %r", 0o0600, dst)
        os.chmod(dst, 0o0600)
        

def add_p12(p12, dir, name='identity'):
    logger = logging.getLogger(__name__)
    logger.debug("adding p12: %r: %r (name:%r)", p12, dir, name)
    if not os.path.exists(dir):
    	logger.debug("> mkdir %r", dir)
    	os.mkdir(dir)
    # get pksc12 password
    passwd = p12_passwd(p12)
    # extract unencrypted key 
    key = os.path.join(dir, '{0!s}.der'.format(name))
    extract(p12, key, passwd, ['-nodes', '-nocerts'], 'rsa')
    # extract crt
    crt = os.path.join(dir, '{0!s}.crt'.format(name))
    extract(p12, crt, passwd, ['-nokeys', '-clcerts'], 'x509')
    

def p12_passwd(p12, attempts=3):
    logger = logging.getLogger(__name__)
    logger.debug("getting p12 password")
    import getpass
    count = 0
    while count < attempts:
        # prompt user for password
        passwd = getpass.getpass()
        # get info about the pfx file using the password
        pkcs12 = ['openssl', 'pkcs12', '-in', p12, '-info', '-nokeys',
                  '-passin', 'pass:{0}'.format(passwd)]
        p = subprocess.Popen(pkcs12, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
        _, err = p.communicate()
        if p.returncode == 0:
            return passwd
        elif not 'invalid password?' in err:
            logger.error(err)
            raise RuntimeError(err)
        count += 1
    # ran out of attempts
    err = "Invalid password: {0} failed attempt(s)...".format(count)
    logger.error("unable to add p12: %s", err)
    raise ValueError(err)


def extract(p12, outfile, passwd, args, tool):
    logger = logging.getLogger(__name__)
    logger.debug("extracting p12")
    _pass = 'pass:{0}'.format(passwd)
    pkcs = ['openssl', 'pkcs12', '-in', p12, '-passin', _pass] + args
    logger.debug("> %s", _hide_pass(pkcs))
    p = subprocess.Popen(pkcs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cnvrt = ['openssl', tool, '-outform', 'DER', '-out', outfile]
    logger.debug("> %s", " ".join(cnvrt))
    c = subprocess.Popen(cnvrt, stdin=p.stdout, stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)
    out, err = c.communicate()
    if c.returncode != 0:
        e = "unable to convert pem to der: {0}".format(err)
        logger.error(e)
        raise RuntimeError(e)
    # convert file permissions 
    logger.debug("> chmod: %o: %r", 0o0600, outfile)
    os.chmod(outfile, 0o0600)
    return outfile


def run():
    """
    Attempt at script level recursion and daemonization
    Benefits, would reduce the number of launchagents and the 
    Accessiblity access
    """
    logger = logging.getLogger(SCRIPT)
    logger.info("starting automation")
    manager = aeios.DeviceManager()
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
    
    # This might lead to some slightly insane recursion, 
    # assuming it works at all
    resource = resources.Resources()
    logfile = os.path.join(resource.logs, "aeiosutil.log")
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
    pass
    # main()
