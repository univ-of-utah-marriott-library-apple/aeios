#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import subprocess
# import logging
import unittest

import argparse

'''Something descriptive
'''

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = ('Copyright (c) 2019 ' 
                 'University of Utah, Marriott Library')
__license__ = 'MIT'
__version__ = '0.0.0'
__url__ = None
__description__ = 'tests for argument parsing'

## CHANGE LOG:
#

def usage():
    '''return usage message
    '''
    _usage = '''{0}
    '''
    return usage.format(os.path.basename(__file__))

class Parser(argparse.ArgumentParser):
    '''Overwrite error handling for argparse.ArgumentParser()
    '''
    def error(self, msg):
        print("ERROR: {0}\n".format(msg), file=sys.stderr)
        helpmsg = usage()
        raise SystemExit(helpmsg)

class TestParser(unittest.TestCase):

    def setUp(self):
        self.parser = argparse.ArgumentParser(add_help=False)
        self.parser.add_argument('-h', '--help', action='store_true')


    def tearDown(self):
        self.parser = None

    def test_help(self):
        args = self.parser.parse_args(['--help'])
        self.assertTrue(args.help)

    def test_additional(self):
        args = self.parser.parse_args(['--help', 'more'])
        try:
            self.assertTrue(args.help)
        except SystemExit:
            helpmsg = usage()
            SystemExit(helpmsg)
        # print(args)

def main():
    pass
    # print("hello world")

if __name__ == '__main__':
    unittest.main(verbosity=2)

