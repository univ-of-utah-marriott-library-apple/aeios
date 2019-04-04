# -*- coding: utf-8 -*-

"""
Library for iOS Device tethering

Mostly Deprecated in macOS 10.13+
"""

import os
import sys
import re
import subprocess
import time
import plistlib
import json
import logging

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright(c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "1.4.3"

ENABLED = None

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())


class Error(Exception):
    pass
    

class TetheringError(Error):
    pass


def _old_tetherator(arg, output=True, **kwargs):
    """
    old style output from `AssetCacheTetheratorUtil`
    
    :param string arg:      argument for `AssetCacheTetheratorUtil`
    :param bool output:     modify return 
    
    :returns: (output=True)     new-style `AssetCacheTetheratorUtil` output 
    :returns: (output=False)    returncode from `AssetCacheTetheratorUtil`
    """
    p, out = assetcachetetheratorutil(arg, json=False, **kwargs)
    if output:
        # modify the output of old `AssetCacheTetheratorUtil` to be 
        # what is returned in the newer version
        universal = ['Checked In', 'Serial Number', 'Check In Pending']
        changed = {'Tethered': 'Bridged', 'Device Name': 'Name',
                   'Check In Retry Attempts': 'Check In Attempts',
                   'Device Location ID': 'Location ID'}
        modified = []
        for device in _parse_tetherator_status(out.rstrip()):
            info = {v:device[k] for k,v in changed.items()}
            info.update({k:device[k] for k in universal})
            # hack for paired (this might be a bad idea overall)
            info['Paired'] = device.get('Paired')
            modified.append(info)
            
        return {'Device Roster': modified}
    else:
        return p.returncode


def _parse_tetherator_status(status):
    """
    Parse output of `AssetCacheTetheratorUtil status`

    (Deprecated in 10.13+)    
    """
    logger = logging.getLogger(__name__)
    # remove newlines and extra whitespace from status
    stripped = re.sub(r'\n|\s{4}', '', status)

    # get dictionary of all devices as a string:
    #   e.g. '{"k" = v; "k2" = v2; "k3" = "v3";}, {...}, ...'
    devices_string = re.search(r'\((.*)\)', stripped).group(1)

    # split devices_string into list of individual dictionary strings:
    #   e.g. ['{"k" = v; "k2" = v2; "k3" = "v3"}', '{...}', ...]
    dict_strings = re.findall(r'\{.+?\}', devices_string)
    logger.debug("found %d device(s)", len(dict_strings))

    tethered_devices = []    
    for d_str in dict_strings:
        # split each dictionary string into key-value pairs:
        # e.g. ['{"k" = "v"', '"k2" = v2', '"k3" = "v3"', ..., '}']
        # split on ';' and skip the last value (always '}')
        tethered_device = {}
        for kvp in d_str.split(';')[0:-1]:
            # split key-value pairs 
            # e.g. ('{"k"','v'), ('"k2"','v2'), or ('"k3"','"v3"'), etc.
            try:
                raw_k,raw_v = kvp.split(" = ")
            except ValueError:
                logger.exception("unable to parse: %r", d_str)
                logger.debug("key-value pair: %r", kvp)
                raise
            try:
                # exclude quotations (if any) from each key
                # first key will still have '{' at the beginning
                k = re.match(r'^\{?"?(.+?)"?$', raw_k).group(1)
            except AttributeError:
                # all information
                logger.exception("unable to parse: %r", d_str)
                logger.debug("unexpected key: %r", raw_k)
                logger.debug("key-value pair: %r", kvp)
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
                logger.exception("unable to parse: %r", d_str)
                logger.debug("key-value pair: %r", kvp)
                logger.debug("unexpected value: %r", raw_v)
                raise
            # add each parsed key and value to dict
            tethered_device[k] = v

        tethered_devices.append(tethered_device)

    # return list of all device dicts
    return tethered_devices


def assetcachetetheratorutil(arg, json=True, log=None):
    if not log:
        log = logging.getLogger(__name__)
    cmd = ['/usr/bin/AssetCacheTetheratorUtil']
    if json:
        cmd += ['--json']
    cmd += [arg]
    log.debug("> {0}".format(" ".join(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    out, err = p.communicate()
    # older version of command prints output to stderr
    return (p, out) if json else (p, err)


def _tetherator(arg, output=True, **kwargs):
    """
    10.13+ `AssetCacheTetheratorUtil`
    
    """
    p, out = assetcachetetheratorutil(arg, json=True, **kwargs)
    if output:
        return json.loads(out.rstrip())['result']
    else:
        return p.returncode


# decorator
def dynamic(func):
    """
    decorator to dynamically pick an assign the appropriate 
    function used for returning information about device tethering
    function is only calculated once
    """
    # calculate which version function to use (only calculated once)
    try:
        # --json flag only available in 10.13+
        cmd = ['/usr/bin/AssetCacheTetheratorUtil', '--json', 'status']
        subprocess.check_call(cmd, stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
        # use the newer version
        _func = _tetherator
    except subprocess.CalledProcessError:
        # use the older version
        _func = _old_tetherator
    # I'll be honest, this is witchcraft... see tetherator()
    def wrapper(*args, **kwargs):
        return _func(*args, **kwargs)
    return wrapper


@dynamic
def tetherator():
    """
    function called is determined by the @dynamic decorator
    """
    # NOTE: I find this strange, because I don't define _decorated()
    #       but it doesn't matter what I call: f(), blah(), broken()
    #       ... everything seems to point to the wrapped function
    #           and I'm not quite sure how, or if this will bite me
    # all *args and **kwargs are passed to the decorated function

    #return _decorated()
    
    # NOTE: apparently nothing in this function is ever run (which
    #       is why the call above didn't raise UnboundLocalError)
    pass


# ADDITIONAL TOOLS

def wait_for_devices(previous, timeout=10, poll=2, **kwargs):
    """
    compare items in the previous device list with devices that appear
    """
    logger = logging.getLogger(__name__)
    logger.info("waiting for devices to reappear")
    prev_sn = [d['Serial Number'] for d in previous]
    found = []
    tethered = []
    max = timeout / poll
    count = 0
    
    while count < max:
        current = devices(**kwargs)
        appeared = []
        
        for device in current:
            sn = device['Serial Number']
            name = device['Name']
            
            # modify name for logging 
            if name == 'iPad':
                name += ' ({0})'.format(sn)

            if sn in prev_sn:
                if sn not in found:
                    appeared.append(name)
                    found.append(sn)
            else:
                found.append(sn)

            if device['Checked In']:
                logger.debug("{0} tethered!".format(name))
                tethered.append(sn)
        
        # superfluous logging
        if appeared:
            msg = "device(s) appeared: {0}".format(", ".join(appeared))
            logger.debug(msg)
            
        sn_set = set(found + prev_sn)
        # list of items that 
        waiting = [x for x in sn_set if x not in tethered]

        if not waiting:
            return

        waitmsg = "waiting on {0} device(s)".format(len(waiting))
        waitmsg += ": ({0})".format(", ".join(waiting))
        logger.info(waitmsg)
        count += 1
        time.sleep(poll)

    raise TetheringError("devices never came up: {0}".format(waiting))


def tethered_caching(args):
    """
    Start or stop tethered-caching 
    (Not Supported in macOS 10.13+)
    """
    _bin = '/usr/bin/tethered-caching'
    logger = logging.getLogger(__name__)
    try:
        cmd = ['/usr/bin/sudo', '-n', _bin, args]
        logger.debug("> {0}".format(" ".join(cmd)))
        subprocess.check_call(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        logger.debug("`%s %s`: failed", _bin, " ".join(args))
        logger.error(e)
        raise Error("tethered-caching failed")    


def restart(timeout=30, wait=True, log=None):
    """
    Restart tethered-caching (requires root)
    (Not Supported in macOS 10.13+)
    """
    if not log:
        logger = logging.getLogger(__name__)
    logger.info("restarting tethered caching")
    # get current devices before restarting
    previous = devices()
    
    start()
    logger.info("successfully restarted tethering!")

    if previous and wait:
        wait_for_devices(previous, timeout=timeout)


def start():
    """
    Starts tethered-caching (requires root)
    (Not Supported in macOS 10.13+)
    """
    logger = logging.getLogger(__name__)
    logger.info("starting tethering services")
    tethered_caching('-b')
    logger.debug("successfully started tethering!")


def stop():  
    """
    Stops tethered-caching (requires root)
    (Not Supported in macOS 10.13+)
    """
    logger = logging.getLogger(__name__)
    if not enabled(refresh=False):
        logger.warn("tethering services not running")

    logger.info("stopping tethering services")
    tethered_caching('-k')
    logger.debug("successfully stopped tethering!")


def enabled(refresh=True, log=None, **kwargs):
    """
    :returns: True if device Tethering is enabled, else False
    """
    global ENABLED
    if refresh or ENABLED is None:
        retcode = tetherator('isEnabled', output=False, **kwargs)
        ENABLED = True if retcode == 0 else False
    return ENABLED


def devices(**kwargs):
    """
    shortcut function returning list of all devices found by
    tetherator()
    """
    return tetherator('status', **kwargs)['Device Roster']


def device_is_tethered(sn, **kwargs):
    """
    :returns: True if device with specified serial number is tethered
    """
    if not sn:
        raise Error("no device specified")
    return devices_are_tethered([sn], **kwargs)


def devices_are_tethered(sns, strict=False, **kwargs):
    """
    Use list of devices serial numbers to determine tethering status

    :returns: True if all specified devices are tethered
    """
    logger = logging.getLogger(__name__)
    if not enabled(refresh=False, **kwargs):
        raise Error("tethering is not enabled")

    info = {d['Serial Number']:d for d in devices(**kwargs)}
    _tethered = True
    missing = []
    for sn in sns:
        try:
            device = info[sn]
            if not device['Checked In']:
                _tethered = False
        except KeyError:
            _tethered = False
            missing.append(sn)

    if missing:
        err = "missing device(s): {0}".format(missing)
        logger.error(err)
        if strict:
            raise TetheringError(err)
    
    return _tethered

    all_tethered =  True
    try:
        _queried = [info[sn] for sn in sns]
        _tethered = [v]
    except KeyError:
        err = "missing device: {0}".format(sn)
        logger.error(err)
        raise TetheringError(err)

    for sn in sns:
        try:
            device = info[sn]
            if not device['Checked In']:
                all_tethered = False
        except KeyError:
            err = "missing device: {0}".format(sn)
            logger.error(err)
            raise TetheringError(err)
    
    return all_tethered


if __name__ == '__main__':
    pass
