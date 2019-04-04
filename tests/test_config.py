# -*- coding: utf-8 -*-

import os
import time
import shutil
import plistlib
import unittest
import threading
import datetime as dt

from aeios import config

"""
Tests for aeios.config
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright (c) 2018 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "1.0.2"

# location for temporary files created with tests
LOCATION = os.path.dirname(__file__)
TMPDIR = os.path.join(os.path.dirname(__file__), 'tmp', 'config')

def setUpModule():
    """
    create tmp directory
    """
    try:
        os.mkdir(TMPDIR)
    except OSError as e:
        if e.errno != 17:
            raise
    
def tearDownModule():
    """
    remove tmp directory
    """
    shutil.rmtree(TMPDIR)


class TestConfigInit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = os.path.join(TMPDIR, 'file')
        with open(cls.file, 'w') as f:
            f.write('file')

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.file)

    def setUp(self):
        cls = self.__class__
        self.file = cls.file
        self.path = os.path.join(TMPDIR, 'init')
        self.config = config.Manager(id='init_test', path=self.path)

    def tearDown(self):
        pass
    
    def test_has_file_attribute(self):
        self.assertTrue(self.config.file)

    def test_has_lock_attribute(self):
        self.assertTrue(self.config.lock)

    def test_has_lockfile_attribute(self):
        self.assertTrue(self.config.lockfile)

    def test_lockfile_is_not_file(self):
        self.assertNotEqual(self.config.lockfile, self.config.file)

    def test_lockfile_not_locked(self):
        self.assertFalse(self.config.lock.locked)

    def test_init_does_not_create_file(self):
        self.assertFalse(os.path.exists(self.config.file))

    def test_init_does_not_create_lockfile(self):
        self.assertFalse(os.path.exists(self.config.lockfile))

    def test_init_creates_missing_path(self):
        os.removedirs(self.path)
        self.assertFalse(os.path.exists(self.path))
        conf = config.Manager(id='test2', path=self.path)
        self.assertTrue(os.path.exists(self.path))

    def test_path_exists_as_file_fails(self):
        with self.assertRaises(TypeError):
            conf = config.Manager('test2', path=self.file)


class TestSimpleReadAndWrite(unittest.TestCase):

    def setUp(self):
        cls = self.__class__
        self.path = os.path.join(TMPDIR, 'read-and-write')
        self.config = config.Manager(id='test', path=self.path)

    def tearDown(self):
        try:
            os.remove(self.config.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def test_read_missing_file(self):
        with self.assertRaises(Exception):
            self.config.read()

    def test_write_nothing(self):
        with self.assertRaises(Exception):
            self.config.write()

    def test_write_string(self):
        self.config.write('test')
        data = self.config.read()
        self.assertEquals(data, 'test')

    def test_empty_dict(self):
        self.config.write({})
        data = self.config.read()
        self.assertEquals(data, {})

    def test_empty_list(self):
        self.config.write([])
        data = self.config.read()
        self.assertEquals(data, [])

    def test_list_simple(self):
        self.config.write([1,2,3])
        data = self.config.read()
        self.assertEquals(data, [1,2,3])

    def test_dict_simple(self):
        self.config.write({'test':'simple'})
        data = self.config.read()
        self.assertEquals(data, {'test':'simple'})


class TestUpdate(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(TMPDIR, 'update')
        self.config = config.Manager(id='test', path=self.path)
        
    def tearDown(self):
        try:
            os.remove(self.config.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def test_update_new(self):
        self.config.write({'one': 1})
        self.config.update({'two': 2})
        self.assertEquals(self.config.read(), {'one':1, 'two':2})
    
    def test_update_existing(self):
        self.config.write({'one': 1})
        self.config.update({'one': 2})
        self.assertEquals(self.config.read(), {'one':2})

    def test_update_empty(self):
        self.config.write({'one': 1})
        self.config.update({})
        self.assertEquals(self.config.read(), {'one':1})

    def test_update_returns(self):
        self.config.write({'one': 1})
        result = self.config.update({'two': 2})
        self.assertEquals({'one':1, 'two':2}, result)


class TestGet(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(TMPDIR, 'get')
        self.config = config.Manager(id='test', path=self.path)
        self.config.write({})
        
    def tearDown(self):
        try:
            os.remove(self.config.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def test_get_missing_file(self):
        """
        test Exception is raised when no file exists
        """
        os.remove(self.config.file)
        with self.assertRaises(Exception):
            self.config.get('missing')

    def test_get_missing_with_default(self):
        """
        test default value is returned when key is missing
        """
        result = self.config.get('missing', 'blah')
        self.assertEquals(result, 'blah')

    def test_get_missing_without_default(self):
        """
        test None is returned when no value exists
        """
        result = self.config.get('missing')
        self.assertIsNone(result)

    def test_get_exists(self):
        """
        test existing value is returned
        """
        self.config.write({'exists': 'value'})
        result = self.config.get('exists')
        self.assertEquals(result, 'value')

    def test_get_exists_with_default(self):
        """
        test existing value is returned when default is provided
        """
        self.config.write({'exists': 'value'})
        result = self.config.get('exists', 'blah')
        self.assertEquals(result, 'value')

    def test_get_on_list(self):
        """
        test AttributeError is raised when get is called on list
        """
        self.config.write([])
        with self.assertRaises(AttributeError):
            self.config.get('exists', 'blah')


class TestDelete(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(TMPDIR, 'delete')
        self.config = config.Manager(id='test', path=self.path)
        self.config.write({'key':'value'})
        
    def tearDown(self):
        try:
            os.remove(self.config.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def test_delete_existing(self):
        """
        test key is deleted from config
        """
        result = self.config.delete('key')
        data = self.config.read()
        self.assertEquals(data, {})

    def test_delete_missing(self):
        """
        test KeyError is raised when deleting missing key
        """
        self.config.write({})
        with self.assertRaises(KeyError):
            self.config.delete('key')

    def test_delete_missing_file(self):
        """
        test KeyError is raised when deleting missing key
        """
        os.remove(self.config.file)
        with self.assertRaises(Exception):
            self.config.delete('key')

    def test_delete_returns(self):
        """
        test delete returns the value for the key it's deleting
        """
        result = self.config.delete('key')
        self.assertEquals(result, 'value')

    def test_delete_list(self):
        """
        test index is deleted from list
        """
        self.config.write(['value'])
        value = self.config.delete(0)
        result = self.config.read()
        self.assertEquals(result, [])

    def test_delete_list_retunrs(self):
        """
        test delete returns value on list
        """
        self.config.write(['value'])
        result = self.config.delete(0)
        self.assertEquals(result, 'value')

    def test_delete_list_empty(self):
        """
        test delete raises IndexError on empty list
        """
        self.config.write([])
        with self.assertRaises(IndexError):
            self.config.delete(0)


@unittest.skip("Unfinished")
class TestAppend(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(TMPDIR, 'append')
        self.config = config.Manager(id='test', path=self.path)
        
    def tearDown(self):
        try:
            os.remove(self.config.file)
        except OSError as e:
            if e.errno != 2:
                raise


@unittest.skip("Unfinished")
class TestReset(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(TMPDIR, 'reset')
        self.config = config.Manager(id='test', path=self.path)
        
    def tearDown(self):
        try:
            os.remove(self.config.file)
        except OSError as e:
            if e.errno != 2:
                raise


@unittest.skip("Unfinished")
class TestAdd(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(TMPDIR, 'add')
        self.config = config.Manager(id='test', path=self.path)
        
    def tearDown(self):
        try:
            os.remove(self.config.file)
        except OSError as e:
            if e.errno != 2:
                raise


class TestDeleteKeys(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(TMPDIR, 'delete')
        self.config = config.Manager(id='test', path=self.path)
        template = {'string':'string', 'list':[], 'dict':{}, 
                    'integer': 1, 'boolean': True, 
                    'date': dt.datetime.now(), 'float': 0.5,
                    'data': plistlib.Data('data')}
        self.config.write(template)
        
    def tearDown(self):
        try:
            os.remove(self.config.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def test_deletekeys_missing_file(self):
        """
        test Exception is raised when no file exists
        """
        os.remove(self.config.file)
        with self.assertRaises(config.Error):
            self.config.deletekeys(['missing'])

    def test_deletekeys_on_list(self):
        """
        test Exception is raised when no file exists
        """
        self.config.write(['missing'])
        with self.assertRaises(TypeError):
            self.config.deletekeys(['missing'])

    def test_deletekeys_missing_key(self):
        """
        test Exception is not raised deleting multiple keys
        """
        self.config.deletekeys(['missing'])
        
    def test_deletekeys_partial_missing_key(self):
        """
        test Exception is not raised deleting multiple keys
        """
        self.config.deletekeys(['missing', 'string'])
        data = self.config.read()
        self.assertFalse(data.has_key('missing'))
        self.assertFalse(data.has_key('string'))

    def test_deletekeys_missing_key_returns_empty_dict(self):
        """
        test Exception is not raised deleting multiple keys
        """
        result = self.config.deletekeys(['missing'])
        self.assertEquals(result, {})        

    def test_delete_existing_key(self):
        self.config.deletekeys(['string'])
        data = self.config.read()
        self.assertFalse(data.has_key('string'))
    

class TestSetDefault(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(TMPDIR, 'setdefault')
        self.config = config.Manager(id='test', path=self.path)
        self.config.write({})
        
    def tearDown(self):
        try:
            os.remove(self.config.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def test_setdefault_missing_file(self):
        """
        test Exception is raised when no file exists
        """
        os.remove(self.config.file)
        with self.assertRaises(Exception):
            self.config.setdefault('missing')

    def test_setdefault_missing_with_default(self):
        """
        test default value is returned when key is missing
        """
        result = self.config.setdefault('missing', 'blah')
        self.assertEquals(result, 'blah')

    def test_setdefault_missing_with_default_persists(self):
        """
        test default value is returned when key is missing
        """
        value = self.config.setdefault('missing', 'blah')
        result = self.config.setdefault('missing')
        self.assertEquals(result, 'blah')

    def test_setdefault_missing_without_default(self):
        """
        test None is returned when no value exists
        """
        result = self.config.setdefault('missing')
        self.assertIsNone(result)

    def test_setdefault_missing_no_default_persists(self):
        """
        test None is returned when no value exists
        This gets tricky, because None is not a supported plist value
        """
        self.config.setdefault('missing')
        data = self.config.read()
        with self.assertRaises(Exception):
            result = data['missing']

    def test_setdefault_exists(self):
        """
        test existing value is returned
        """
        self.config.write({'exists': 'value'})
        result = self.config.setdefault('exists')
        self.assertEquals(result, 'value')

    def test_setdefault_exists_with_default(self):
        """
        test existing value is returned when default is provided
        """
        self.config.write({'exists': 'value'})
        result = self.config.setdefault('exists', 'blah')
        self.assertEquals(result, 'value')

    def test_setdefault_exists_with_default_not_changed(self):
        """
        test existing value is returned when default is provided
        """
        self.config.write({'exists': 'value'})
        value = self.config.setdefault('exists', 'blah')
        result = self.config.setdefault('exists')
        self.assertEquals(result, 'value')

    def test_setdefault_on_list(self):
        """
        test AttributeError is raised when get is called on list
        """
        self.config.write([])
        with self.assertRaises(TypeError):
            self.config.setdefault('exists', 'blah')


class TestThreaded(unittest.TestCase):
    """
    Tests involving threading
    """
    def setUp(self):
        self.path = os.path.join(TMPDIR, 'threaded')
        self.config = config.Manager(id='test', path=self.path)
        self.config.write({})
        self.config2 = config.Manager(id='test', path=self.path)
        self.config3 = config.Manager(id='test', path=self.path)
        
    def tearDown(self):
        try:
            os.remove(self.config.file)
        except OSError as e:
            if e.errno != 2:
                raise

    def test_threaded_update(self):
        """
        test threaded config.Managers update as expected
        """
        self.config.write({})
        # function for threading
        update = lambda x,y: x.update(y)
        t1 = threading.Thread(target=update, 
                              args=(self.config2,{'one':1}))
        t1.start()
        t2 = threading.Thread(target=update, 
                              args=(self.config3,{'two':2}))
        t2.start()
        t1.join()
        t2.join()
        time.sleep(.01)
        result = self.config.read()
        self.assertEquals(result, {'one':1, 'two':2})


    def test_threaded_write(self):
        """
        test threaded config.Managers write as expected
        """
        self.config.write({})
        write = lambda x,y: x.write(y)
        t1 = threading.Thread(target=write, 
                              args=(self.config2,{'one':1}))
        t1.start()
        t2 = threading.Thread(target=write, 
                              args=(self.config3,{'two':2}))
        t2.start()
        t1.join()
        t2.join()
        time.sleep(.01)
        result = self.config.read()
        self.assertEquals(result, {'two':2})


class TestLocking(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(TMPDIR, 'locking')
        self.config = config.Manager(id='test', path=self.path, timeout=0)
        self.config.write({})
        self.lock = config.FileLock(self.config.lockfile, timeout=1)

    def test_double_lock(self):
        with self.lock.acquire():
            with self.lock.acquire(timeout=0):
                pass

    def test_write_locked(self):
        with self.lock.acquire():
            with self.assertRaises(config.TimeoutError):
                self.config.write({})
        
    def test_read_locked(self):
        with self.lock.acquire():
            with self.assertRaises(config.TimeoutError):
                data = self.config.read()
        

if __name__ == '__main__':
    unittest.main(verbosity=1)
