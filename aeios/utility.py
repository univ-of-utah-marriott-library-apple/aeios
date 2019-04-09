# -*- coding: utf-8 -*-

import os
import re
import shutil
import logging
import argparse
import subprocess

from . import resources

"""
Utility functions for aeios
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "1.0.2"

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())


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
        self.add()
        self.remove()
        # self.info()
        # self.list()
        self.configure()

    def add(self):
        """
        add parsers for `aeioutil add`
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

        # aeioutil add app APP
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
        Add parsers for aeioutil remove
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
        
        # aeioutil remove app APP
        # Namespace(cmd='remove', item='app', name=<NAME>)
        app = sp.add_parser('app', help='remove apps',
                            description='remove apps from automation')
        
        app.add_argument('name', metavar='APP', 
                         help='iTunes name of APP (as seen in VPP)')

        # aeioutil remove identity
        # Namespace(cmd='remove', item='identity')
        _id = sp.add_parser('identity', help='remove supervision identity',
                            description='remove supervision identity files')

        # aeioutil remove image (--background | --alert | --lock | --all)
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

        # aeioutil remove wifi
        # Namespace(cmd='remove', item='wifi')
        wifi = sp.add_parser('wifi',  help='remove Wi-Fi profile',
                             description='Wi-Fi profile for DEP enrollment')

        # aeioutil remove reporting
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

        # aeioutil configure slack [--name NAME] URL CHANNEL
        # Namespace(cmd='configure', item='slack', URL=<URL>, 
        #           channel=<CHANNEL>, name=<aeios|NAME>)
        slack = sp.add_parser('slack', help='configure slack', 
                              description='configure slack reporting settings')

        slack.add_argument('URL', help='slack url')
        slack.add_argument('channel', help='slack channel')
        slack.add_argument('--name', default='aeios',
                           help='name of the reporter')

        # aeioutil configure idle SECONDS
        # Namespace(cmd='configure', item='idle', seconds=<SECONDS>)
        idle = sp.add_parser('idle', help='configure idle timer', 
                              description='configure time between idle runs')
        idle.add_argument('seconds', metavar='SECONDS',
                          help='time (in seconds) between idle run')
        
    def parse(self, argv):
        """
        :param argv: list of arguments to parse
        :return: 
        """
        return self.parser.parse_args(argv)


# FUNCTIONS

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


if __name__ == '__main__':
    pass
