#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function

'''functions for tethered-caching
'''

import os
import sys
import re
import subprocess
import time

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '1.0.0'
__url__ = None
__description__ = 'functions for tethered-caching'


class TetheringError(Exception):
    pass


def tetherator(log, arg, output=True):
    '''get output from `AssetCacheTetheratorUtil`
    if output is set to false, returncode is returned
    '''
    cmd = ['/usr/bin/AssetCacheTetheratorUtil', arg]
    log.debug("> {0}".format(" ".join(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    out, err = p.communicate()
    # AssetCacheTetheratorUtil prints information to STDERR
    if output:
        return err.rstrip()
    else:
        return p.returncode

def parse_tetherator_status(log, status):
    '''re-write of parse_tetherator (more complete parser)
    Does its best to convert output of `AssetCacheTetheratorUtil status`
    into a python dictionary regardless of keys and values.
    '''

    # remove newlines and extra whitespace from status
    stripped = re.sub(r'\n|\s{4}', '', status)

    # get dictionary of all devices as a string:
    #   '{"k" = v; "k2" = v2; "k3" = "v3";}, {...}, ...'
    devices_string = re.search(r'\((.*)\)', stripped).group(1)

    # split devices_string into list of individual dictionary strings:
    #   ['{"k" = v; "k2" = v2; "k3" = "v3"}', '{...}', ...]
    dict_strings = re.findall(r'\{.+?\}', devices_string)
    log.debug("found {0} device(s)".format(len(dict_strings)))

    tethered_devices = []    
    for d_str in dict_strings:
        # split each dictionary string into key-value pairs:
        # ['{"k" = "v"', '"k2" = v2', '"k3" = "v3"', ..., '}']
        # split on ';' and skip the last value (always '}')
        tethered_device = {}
        for kvp in d_str.split(';')[0:-1]:
            # split key-value pairs 
            # ('{"k"','v'), ('"k2"','v2'), or ('"k3"','"v3"'), etc.
            try:
                raw_k,raw_v = kvp.split(" = ")
            except ValueError:
                log.error("unable to parse: {0!r}".format(d_str))
                log.error("key-value pair: {0!r}".format(kvp))
                raise
            try:
                # exclude quotations (if any) from each key
                # first key will still have '{' at the beginning
                k = re.match(r'^\{?"?(.+?)"?$', raw_k).group(1)
            except AttributeError:
                # all information
                log.error("unable to parse: {0!r}".format(d_str))
                log.error("key-value pair: {0!r}".format(kvp))
                log.error("unexpected key: {0!r}".format(raw_k))
                raise
            try:
                # exclude quotations (if any), convert various types
                # of values (Yes|No -> bool, digits -> int)
                v = re.match(r'^"?(.+?)"?$', raw_v).group(1)
                if re.match(r'\d+', v):
                    # convert "all integer" values to ints
                    v = int(v)
                elif re.match(r'Yes|No', v):
                    # convert 'Yes' or 'No' strings to True or False
                    v = True if v == 'Yes' else False
            except AttributeError:
                # all information
                log.error("unable to parse: {0!r}".format(d_str))
                log.error("key-value pair: {0!r}".format(kvp))
                log.error("unexpected value: {0!r}".format(raw_v))
                raise
            # add each parsed key and value to dict
            tethered_device[k] = v

        tethered_devices.append(tethered_device)

    # return list of all device dicts
    return tethered_devices
    
def parse_tetherator(log):
    '''incomplete parser but should get SN, name, and tether status

    returns a list of dictionaries for each device

    returns an empty list if no devices are found

    NOTE: I don't know how robust this is...
    '''
    status = tetherator('status')

    # remove newlines and extra whitespace
    stripped = re.sub(r'\n|\s{4}', '', status)
    
    devices = []
    # get list of attached devices (empty list if no devices are found)
    try:
        # try to raise AttributeError as early as possible
        list = re.search(r'\((.*)\)', stripped).group(1)
        for d in re.findall(r'\{[^\}]+\}', list):
            device = {}
            # get device name (with or without quotes)
            n = re.search(r'"Device Name" = "?([^";]+)"?;', d)
            # get serialnumber
            sn = re.search(r'"Serial Number" = ([^;]+);', d)
            # get tethered
            t = re.search(r'Tethered = (Yes|No);', d)
            tethered = True if t.group(1) == 'Yes' else False

            device['Device Name'] = n.group(1)
            device['Seral Number'] = sn.group(1)
            device['Tethered'] = tethered
            devices.append(device)

    except AttributeError as e:
        log.error("unable to parse output: {0}".format(e))
        raise TetherError(e)
    
    return devices

def wait_for_devices(log, prev, timeout=10):
    '''compare items in the previous device list with devices that
    appear
    '''
    log.info("waiting for devices to reappear")
    prev_sn = [d['Serial Number'] for d in prev]
    found = []
    tethered = []
    count = 0

    while count < timeout:
        time.sleep(2)
        current = devices(log)
        for d in current:
            sn = d['Serial Number']
            name = d['Device Name']

            if sn in prev_sn:
                if sn not in found:
                    log.debug("{0} reappeared!".format(name))
                    found.append(sn)
            else:
                found.append(sn)
                log.debug("new device: {0} appeared!".format(name))

            
            if d['Tethered']:
                log.debug("{0} tethered!".format(name))
                tethered.append(sn)
            else:
                log.debug("{0} still connecting...".format(name))

        sn_set = set(found + prev_sn)
        waiting = [x for x in sn_set if x not in tethered]
        if not waiting:
            return
        log.info("still waiting on {0} device(s)".format(len(waiting)))
        count += 1

    raise TetheringError("devices never came up: {0}".format(waiting))

def restart(log, timeout=20):
    '''disables and re-enables tethered-caching (requires root)
    raises subprocess.CalledProcessError if anything goes awry
    '''
    log.info("restarting tethered caching")
    # get current devices before restarting
    previous = devices(log)

    stop(log)
    start(log)
    log.debug("tethered-caching restarted successfully")

    try:
        wait_for_devices(log, previous, timeout=timeout)
    except TetheringError:
        log.error("some devices never came back up")

def start(log):
    '''Starts tethered-caching (requires root)
    '''
    log.debug("starting tethered-caching")
    try:
        cmd = ['sudo', '/usr/bin/tethered-caching', '-b']
        log.debug("> {0}".format(" ".join(cmd)))
        subprocess.check_call(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        log.error("unable to start tethered-caching")
        log.error(e)
        raise  
    log.info("tethered-caching started")

def stop(log):  
    '''Stops tethered-caching (requries root)
    '''

    log.debug("stopping tethered-caching")
    try:
        cmd = ['sudo', '/usr/bin/tethered-caching', '-k']
        log.debug("> {0}".format(" ".join(cmd)))
        subprocess.check_call(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        log.error("unable to stop tethered-caching")
        log.error(e)
        raise
    log.info("tethered-caching stopped")
    
def enabled(log):
    '''Returns True if Tetherator is enabled, else False
    '''
    returncode = tetherator(log, 'isEnabled', output=False)
    return True if returncode == 0 else False

def devices(log):
    '''shortcut function returning list of all devices found by the
    Tetherator
    '''
    status = tetherator(log, 'status')
    all_devices = parse_tetherator_status(log, status)
    return all_devices

def device_is_tethered(log, sn):
    '''Use device serial number to return boolean of tethered status
    '''
    for device in devices(log):
        if device['Serial Number'] == sn:
            return device['Tethered']
    
    err = "no tethering status for device: {0}".format(sn)
    raise TetheringError(err)

def devices_are_tethered(log, sns):
    '''Use device serial number to return boolean of tethered status
    '''
    all_tethered = True
    for device in devices(log):
        for sn in sns:
            if device['Serial Number'] == sn:
                if not device['Tethered']:
                    all_tethered = False
    
    return all_tethered
      
if __name__ == '__main__':
    pass

