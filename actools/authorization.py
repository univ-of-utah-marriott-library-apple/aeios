from __future__ import print_function

import os
import subprocess
import logging
import json
import pprint

class Error(Exception):
    pass


class AuthorizationError(Error):
    pass


class Authorization(object):

    def __init__(self, cert, pkey):
        self.cert = cert
        self.key = pkey

    def args(self):
        '''returns list of arguments for use with cfgutil
        '''
        return ['-C', self.cert, '-K', self.key]


def psck12(p12file, passwd):
    '''returns Authorization object from p12 file
    '''
    pass

def required(command):
    '''returns True if specifed subcommand requires authentication
    '''
    cmds = ['add-tags', 'activate', 'get-unlock-token',
            'install-app', 'install-profile',
            'remove-profile', 'restart', 'restore',
            'restore-backup', 'shut-down', 'wallpaper']
    if command in cmds:
        return True
