import os
import plistlib
# import filelock
import logging
import fcntl
import threading
import time

__all__ = [
    'Manager', 
    'FileLock',
    'TimeoutError',
    'ConfigError'
]

class Error(Exception):
    pass


class ConfigError(Error):
    pass


class TimeoutError(Error):
    '''Raised when lock could not be acquired before timeout
    '''
    def __init__(self, lockfile):
        self.file = lockfile

    def __str__(self):
        return "{0}: lock could not be acquired".format(self.file)


class ReturnProxy(object):
    '''Wrap the lock to make sure __enter__ is not called twice
    when entering the with statement.
    
    If we would simply return *self*, the lock would be acquired
    again in the *__enter__* method of the BaseFileLock, 
    but not released again automatically.
    (Not sure if this is pertinant, but it definitely breaks without it)
    '''
    def __init__(self, lock):
        self.lock = lock
    def __enter__(self):
        return self.lock
    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()


class FileLock(object):
    '''Unix filelocking 
    Adapted from py-filelock, by Benedikt Schmitt
    https://github.com/benediktschmitt/py-filelock
    '''
    def __init__(self, file, timeout=-1):
        self._file = file
        self._fd = None
        self._timeout = timeout
        self._thread_lock = threading.Lock()
        self._counter = 0

    @property
    def file(self):
        '''Return lockfile path
        '''
        return self._file

    @property
    def timeout(self):
        '''Return the value (in seconds) of the timeout
        '''
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        '''Seconds to wait before raising TimeoutError()
        a negative timeout will disable the timeout
        a timeout of 0 will allow for one attempt acquire the lock
        '''        
        self._timeout = float(value)

    @property
    def locked(self):
        '''True, if the object holds the file lock
        '''
        return self._fd is not None
    
    def _acquire(self):
        '''Unix based locking using fcntl.flock(LOCK_EX | LOCK_NB)
        '''
        flags = os.O_RDWR | os.O_CREAT | os.O_TRUNC
        fd = os.open(self._file, flags, 0644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            self._fd = fd
        except (IOError, OSError):
            os.close(fd)

    def _release(self):
        '''Unix based unlocking using fcntl.flock(LOCK_UN)
        '''
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)
        self._fd = None

    def acquire(self, timeout=None, poll_intervall=0.05):
        if not timeout:
            timeout = self.timeout
        with self._thread_lock:
            self._counter += 1

        start = time.time()
        try:
            while True:
                with self._thread_lock:
                    if not self.locked:
                        self._acquire()
                if self.locked:
                    break
                elif timeout >= 0 and (time.time() - start) > timeout:
                    raise TimeoutError(self._file)
                else:
                    time.sleep(poll_intervall)
        except:
            with self._thread_lock:
                self._counter = max(0, self._counter-1)
            raise

        return ReturnProxy(lock=self)

    def release(self, force=False):
        '''Release the lock.

        Note, that the lock is only completly released, if the 
        lock counter is 0
        
        lockfile is not automatically deleted.

        :arg bool force:
            If true, the lock counter is ignored and the lock is 
            released in every case.
        '''
        with self._thread_lock:
            if self.locked:
                self._counter -= 1
                if self._counter == 0 or force:
                    self._release()
                    self._counter = 0

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __del__(self):
        self.release(force=True)


class Manager(object):
    '''This class is meant to allow scripts to read and serialize 
    configuration files.

    The configuration files themselves are modified via filelocking to 
    prevent them from being mangled when being accessed by multiple 
    scripts.
    
    :param id: the configuration identifier
    :type id: str

    EXAMPLE:
        conf = config.Manager("foo")  # initializes the config manager
        try:
            settings = conf.read()   # read the config file
        except config.Error:
            settings = {}
    
        settings['foo'] = 'bar'        
        
        conf.write(settings)         # serialize the modified settings
    
    All serialization files will be written to: 
        /user/specified/directory (path specified at instantiation)
        /Library/Management/Configuration
        ~/Library/Management/Configuration
    '''
    TMP = '/tmp/config'
    
    def __init__(self, id, path=None, logger=None, **kwargs):
        '''Setup the configuration manager. Checks to make sure a 
        configuration directory exists (creates directory if not)
        '''
        if not logger:
            logger = logging.getLogger(__name__)
            logger.addHandler(logging.NullHandler())
        self.log = logger
        lockdir = self.__class__.TMP
        if not os.path.exists(lockdir):
            os.mkdir(lockdir)
        management = 'Library/Management/Configuration'
        homefolder = os.path.expanduser('~')
        directories = [os.path.join('/', management), 
                       os.path.join(homefolder, management)]
        if path:
            if os.path.isfile(path):
                raise TypeError("not a directory: {0}".format(path))
            try:
                dir = check_and_create_directories([path])
            except ConfigError as e:
                if os.path.isdir(path) and os.access(path, os.R_OK):
                    dir = path
                else:
                    raise e
                    
        else:
            # create the config directory if it doesn't exist
            dir = check_and_create_directories(directories)  
        self.file = os.path.join(dir, "{0}.plist".format(id))
        ## create a lockfile to block race conditions
        self.lockfile = "{0}/{1}.lockfile".format(lockdir, id)
        # self.lock = filelock.FileLock(self.lockfile, **kwargs)
        self.lock = FileLock(self.lockfile, **kwargs)


    def write(self, data):
        '''Serializes specified settings to file
        '''
        with self.lock.acquire():
            plistlib.writePlist(data, self.file)
                
    def read(self):
        '''Returns Python data structure as read from disk
        raises ConfigError if unable to read
        '''
        if not os.path.exists(self.file):
            raise ConfigError("file missing: {0}".format(self.file))

        with self.lock.acquire():
            return plistlib.readPlist(self.file)

    # TYPE SPECIFIC FUNCTIONS
    def get(self, key, default=None):
        with self.lock.acquire():
            data = self.read()
            return data.get(key, default)
    
    def update(self, value):
        '''read data from file, update data, and write back to file
        '''
        with self.lock.acquire():        
            data = self.read()
            data.update(value)
            self.write(data)
            return data

    def delete(self, key):
        '''read data from file, update data, and write back to file
        '''
        with self.lock.acquire():        
            data = self.read()
            v = data.pop(key)
            self.write(data)
            return v

    def deletekeys(self, keys):
        '''remove specified keys from file (if they exist)
        returns old values as dictionary
        '''
        with self.lock.acquire():        
            data = self.read()
            _old = {}
            for key in keys:
                try:
                    _old[key] = data.pop(key)
                except KeyError:
                    pass
            self.write(data)
            return _old
            
    # EXPERIMENTAL
    def reset(self, key, value):
        '''this is poor design, but I'm going to leave it for now
        overwrites existing key with value
        returns previous value
        '''
        with self.lock.acquire():        
            data = self.read()
            previous = data[key]
            data[key] = value
            self.write(data)
            return previous

    def append(self, value):
        with self.lock.acquire():        
            data = self.read()
            data.append(value)
            self.write(data)
            return data

    def remove(self, key, value=None):
        with self.lock.acquire():        
            data = self.read()
            if value:                
                if isinstance(data[key], list):
                    data[key].remove(value)
                elif isinstance(data[key], dict):
                    data[key].pop(value)
            else:
                if isinstance(data, list):
                    data.remove(value)
                elif isinstance(data, dict):
                    data.pop(value)
            
            self.write(data)

    def add(self, key, value):
        with self.lock.acquire():        
            data = self.read()
            try:
                for i in value:
                    if i not in data[key]:
                        data[key].append(i)
            except:
                data[key].append(value)
            self.write(data)

    def setdefault(self, key, default=None):
        with self.lock.acquire():
            data = self.read()
            try:
                return data[key]
            except KeyError:
                data[key] = default
                if default is not None:
                    self.write(data)
                return default


def check_and_create_directories(dirs, mode=0755):
    '''checks list of directories to see what would be a suitable place
    to write the configuration file
    '''
    for path in dirs:
        try:
            os.makedirs(path, mode)
            return path
        except OSError as e:
            if e.errno == 17 and os.access(path, os.W_OK):
                # directory already exists and is writable
                return path
    ## exhausted all options
    raise ConfigError("no suitable directory was found for config")
    
## MAIN ##
def main():
    return 0

if __name__ == '__main__':
    main()

