#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import plistlib
import threading
import time
import unittest
from datetime import datetime

'''Tests for ipadmanager.tasklist
'''

import config
from config import FileLock
from tasklist import TaskList

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '1.0.1'
__url__ = None
__description__ = 'Tests for ipadmanager.tasklist'

## location for temporary files created with tests
TMPDIR = os.path.join(os.path.dirname(__file__), 'tmp')

def setUpModule():
    '''create tmp directory
    '''
    try:
        os.mkdir(TMPDIR)
    except OSError as e:
        if e.errno != 17:
            raise
    
def tearDownModule():
    '''Remove tmp directory
    '''
    shutil.rmtree(TMPDIR)


class BaseTestCase(unittest.TestCase):
    
    file = None

    @classmethod
    def setUpClass(cls):
        cls.path = TMPDIR
        
    @classmethod
    def tearDownClass(cls):
        pass
        
    def setUp(self):
        self.id = 'edu.utah.mlib.ipad.tasks'
        self.path = self.__class__.path 
        self.task = TaskList(self.id, path=self.path)
        self.file = self.task.file
        self.ecids = ['0xAABBCCDDEEFF11', '0xAABBCCDDEEFF12']
        self.only = ['0xAABBCCDDEEFF13']

    def tearDown(self):
        try:
            os.remove(self.file)
        except OSError as e:
            if e.errno != 2:
                raise

class TestTaskListFile(BaseTestCase):

    def test_task_file_exists(self):
        self.assertTrue(os.path.exists(self.task.file))


class TestTaskListBasic(BaseTestCase):
        
    def test_add(self):
        ecids = [self.ecids[0]]
        self.task.add('test', ecids)
        erase = self.task.list('test')
        self.assertItemsEqual(ecids, erase)

    def test_add_empty_list(self):
        self.task.add('erase', [])
        self.assertEquals(self.task.record['erase'], [])

    def test_add_empty_set(self):
        self.task.add('prepare', set([]))
        self.assertEquals(self.task.record['prepare'], [])

    def test_add_none(self):
        with self.assertRaises(TypeError):
            self.task.add('install', None)

    def test_add_string(self):
        with self.assertRaises(TypeError):
            self.task.add('install', 'string')

    def test_add_duplicate_ignored(self):
        self.task.add('install', self.ecids)
        self.task.add('install', self.ecids)
        result = self.task.record['install']
        self.assertItemsEqual(self.ecids, result)

    def test_add_missing_key(self):
        self.task.add('test', self.ecids)
        self.assertTrue(self.task.record['test'])


    def test_list_empty(self):
        empty = self.task.list('test')
        self.assertEquals([], empty)

    def test_list_missing_key_returns_empty(self):
        result = self.task.list('missing')
        self.assertEquals(result, [])

    def test_list_missing_key_no_key(self):
        result = self.task.list('missing')
        self.assertEquals(result, [])
        with self.assertRaises(KeyError):
            self.task.record['missing']

    def test_list_does_not_empty_task(self):
        ecids = [self.ecids[0]]
        self.task.add('erase', ecids)
        list = self.task.list('erase')
        self.assertTrue(self.task.list('erase'))

    def test_list_only(self):
        self.task.add('erase', self.ecids + self.only)
        list = self.task.list('erase', only=self.only)
        self.assertEquals(list, self.only)

    def test_list_exclude(self):
        self.task.add('erase', self.ecids + self.only)
        list = self.task.list('erase', exclude=self.only)
        self.assertItemsEqual(list, self.ecids)

    def test_list_exclude_only(self):
        self.task.add('erase', self.ecids + self.only)
        list = self.task.list('erase', exclude=self.ecids, 
                              only=self.only)
        self.assertEquals(list, self.only)

    def test_list_only_empty(self):
        self.task.add('erase', self.ecids + self.only)
        list = self.task.list('erase', exclude=self.ecids, 
                              only=[])
        self.assertEquals(list, [])



    def test_get_empty(self):
        empty = self.task.get('test')
        self.assertEquals([], empty)

    def test_get_missing_key_returns_empty(self):
        result = self.task.get('missing')
        self.assertEquals(result, [])

    def test_get_missing_key_no_key(self):
        result = self.task.get('missing')
        self.assertEquals(result, [])
        with self.assertRaises(KeyError):
            self.task.record['missing']

    def test_get_missing_key_with_excluded_non_modified(self):
        result = self.task.get('missing', exclude=['bad'])
        self.assertEquals(result, [])
        with self.assertRaises(KeyError):
            self.task.record['missing']


    def test_get_exclude(self):
        excluded = [self.ecids[0]]
        self.task.add('install', self.ecids)
        self.task.get('install', excluded)
        result = self.task.list('install')
        self.assertItemsEqual(excluded, result)

    def test_get_empty_with_excluded(self):
        result = self.task.get('install', self.ecids)
        self.assertItemsEqual(result, [])
        _list = self.task.list('install')
        self.assertItemsEqual(_list, [])

    def test_get_exclude_does_not_return_excluded(self):
        excluded = [self.ecids[0]]
        expected = [self.ecids[1]]
        self.task.add('install', self.ecids)
        result = self.task.get('install', excluded)
        self.assertItemsEqual(result, expected)

    def test_get_exclude_does_change_task(self):
        excluded = [self.ecids[0], 'bad']
        self.task.add('install', self.ecids)
        result = self.task.get('install', excluded)
        self.assertNotIn('bad', result)
        result = self.task.list('install')
        self.assertNotIn('bad', result)

    ## test for only flag
    def test_get_only_empty(self):
        self.task.add('erase', self.ecids)
        result = self.task.get('erase', exclude=self.ecids, 
                              only=[])
        self.assertEquals(result, [])
        result = self.task.list('erase')
        self.assertItemsEqual(result, self.ecids)

    def test_get_only(self):
        self.task.add('install', self.ecids + self.only)
        result = self.task.get('install', only=self.only)
        self.assertEquals(self.only, result)
        result = self.task.list('install')
        self.assertItemsEqual(result, self.ecids)
        
    def test_get_only_exclude(self):
        self.task.add('install', self.ecids + self.only)
        result = self.task.get('install', exclude=[self.ecids[0]], 
                                only=self.ecids)
        self.assertEquals([self.ecids[1]], result)
        result = self.task.list('install')
        self.assertItemsEqual(result, [self.ecids[0]] + self.only)
        
    def test_get_only_missing_exclude(self):
        self.task.add('install', self.ecids)
        result = self.task.get('install', exclude=[self.ecids[0]], 
                                only=self.only)
        self.assertEquals([], result)
        result = self.task.list('install')
        self.assertItemsEqual(result, self.ecids)
        

    def test_add_get_list(self):
        self.task.add('erase', self.ecids)
        self.assertTrue(self.task.list('erase'))
        result = self.task.get('erase')
        self.assertItemsEqual(result, self.ecids)
        self.assertTrue(result)
        self.assertFalse(self.task.list('erase'))

    def test_get_task(self):
        self.task.add('erase', self.ecids)
        result = self.task.get('erase')
        self.assertItemsEqual(self.ecids, result)

    def test_get_empties_task(self):
        self.task.add('erase', self.ecids)
        returned = self.task.get('erase')
        self.assertFalse(self.task.list('erase'))


class TestTaskListErase(BaseTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.assertEquals(self.task.list('erase'), [])
        
    def test_erase_add(self):
        self.task.erase(self.ecids)
        result = self.task.list('erase')
        self.assertItemsEqual(result, self.ecids)

    def test_erase_add_duplicate(self):
        self.task.erase(self.ecids)
        self.task.erase(self.ecids)
        result = self.task.list('erase')
        self.assertItemsEqual(result, self.ecids)

    def test_erase_add_empty(self):
        self.task.erase([])
        result = self.task.list('erase')
        self.assertEquals(result, [])
   
    def test_erase_add_excluded(self):
        excluded = [self.ecids[0]]
        expected = [self.ecids[1]]
        self.task.erase(self.ecids, exclude=excluded)
        result = self.task.list('erase')
        self.assertEquals(result, expected)
   
    def test_erase_add_empty_excluded(self):
        excluded = [self.ecids[0]]
        self.task.erase([], exclude=excluded)
        result = self.task.list('erase')
        self.assertEquals(result, [])
   
    def test_erase_get(self):
        self.task.erase(self.ecids)
        result = self.task.erase()
        self.assertItemsEqual(result, self.ecids)
        self.assertFalse(self.task.list('erase'))
   
    def test_erase_get_excluded(self):
        excluded = [self.ecids[0]]
        expected = [self.ecids[1]]
        self.task.erase(self.ecids)
        result = self.task.erase(exclude=excluded)
        self.assertEquals(result, expected)
        self.assertItemsEqual(self.task.list('erase'), excluded)
   
    def test_erase_get_excluded_missing(self):
        expected = self.ecids
        self.task.erase(self.ecids)
        result = self.task.erase(exclude=['missing'])
        self.assertItemsEqual(result, expected)
        self.assertItemsEqual(self.task.list('erase'), [])
   

class TestTaskListPrepare(BaseTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.assertEquals(self.task.list('prepare'), [])
        
    def test_prepare_add(self):
        self.task.prepare(self.ecids)
        result = self.task.list('prepare')
        self.assertItemsEqual(result, self.ecids)

    def test_prepare_add_duplicate(self):
        self.task.prepare(self.ecids)
        self.task.prepare(self.ecids)
        result = self.task.list('prepare')
        self.assertItemsEqual(result, self.ecids)
   
    def test_prepare_add_empty(self):
        self.task.prepare([])
        result = self.task.list('prepare')
        self.assertEquals(result, [])
   
    def test_prepare_add_excluded(self):
        excluded = [self.ecids[0]]
        expected = [self.ecids[1]]
        self.task.prepare(self.ecids, exclude=excluded)
        result = self.task.list('prepare')
        self.assertEquals(result, expected)
   
    def test_prepare_add_empty_excluded(self):
        excluded = [self.ecids[0]]
        self.task.prepare([], exclude=excluded)
        result = self.task.list('prepare')
        self.assertEquals(result, [])
   
    def test_prepare_get(self):
        self.task.prepare(self.ecids)
        result = self.task.prepare()
        self.assertItemsEqual(result, self.ecids)
        self.assertFalse(self.task.list('prepare'))
   
    def test_prepare_get_excluded(self):
        excluded = [self.ecids[0]]
        expected = [self.ecids[1]]
        self.task.prepare(self.ecids)
        result = self.task.prepare(exclude=excluded)
        self.assertEquals(result, expected)
        self.assertItemsEqual(self.task.list('prepare'), excluded)
   
    def test_prepare_get_excluded_missing(self):
        expected = self.ecids
        self.task.prepare(self.ecids)
        result = self.task.prepare(exclude=['missing'])
        self.assertItemsEqual(result, expected)
        self.assertItemsEqual(self.task.list('prepare'), [])
   

class TestTaskListApps(BaseTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.assertEquals(self.task.list('installapps'), [])
        
    def test_apps_add(self):
        self.task.installapps(self.ecids)
        result = self.task.list('installapps')
        self.assertItemsEqual(result, self.ecids)

    def test_apps_add_duplicate(self):
        self.task.installapps(self.ecids)
        self.task.installapps(self.ecids)
        result = self.task.list('installapps')
        self.assertItemsEqual(result, self.ecids)

    def test_apps_add_empty(self):
        self.task.installapps([])
        result = self.task.list('installapps')
        self.assertEquals(result, [])
   
    def test_apps_add_excluded(self):
        excluded = [self.ecids[0]]
        expected = [self.ecids[1]]
        self.task.installapps(self.ecids, exclude=excluded)
        result = self.task.list('installapps')
        self.assertEquals(result, expected)
   
    def test_apps_add_empty_excluded(self):
        excluded = [self.ecids[0]]
        self.task.installapps([], exclude=excluded)
        result = self.task.list('installapps')
        self.assertEquals(result, [])
   
    def test_apps_get(self):
        self.task.installapps(self.ecids)
        result = self.task.installapps()
        self.assertItemsEqual(result, self.ecids)
        self.assertFalse(self.task.list('installapps'))
   
    def test_apps_get_excluded(self):
        excluded = [self.ecids[0]]
        expected = [self.ecids[1]]
        self.task.installapps(self.ecids)
        result = self.task.installapps(exclude=excluded)
        self.assertEquals(result, expected)
        self.assertItemsEqual(self.task.list('installapps'), excluded)
   
    def test_apps_get_excluded_missing(self):
        expected = self.ecids
        self.task.installapps(self.ecids)
        result = self.task.installapps(exclude=['missing'])
        self.assertItemsEqual(result, expected)
        self.assertItemsEqual(self.task.list('installapps'), [])
   

class TestTaskListFinished(BaseTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.assertEquals(self.task.list('finished'), [])
        
    def test_finished_add(self):
        self.task.finished(self.ecids)
        result = self.task.list('finished')
        self.assertItemsEqual(result, self.ecids)

    def test_finished_add_duplicate(self):
        self.task.finished(self.ecids)
        self.task.finished(self.ecids)
        result = self.task.list('finished')
        self.assertItemsEqual(result, self.ecids)

    def test_finished_add_empty(self):
        self.task.finished([])
        result = self.task.list('finished')
        self.assertEquals(result, [])
   
    def test_finished_add_excluded(self):
        excluded = [self.ecids[0]]
        expected = [self.ecids[1]]
        self.task.finished(self.ecids, exclude=excluded)
        result = self.task.list('finished')
        self.assertEquals(result, expected)
   
    def test_finished_add_empty_excluded(self):
        excluded = [self.ecids[0]]
        self.task.finished([], exclude=excluded)
        result = self.task.list('finished')
        self.assertEquals(result, [])
   
    def test_finished_get(self):
        self.task.finished(self.ecids)
        result = self.task.finished()
        self.assertItemsEqual(result, self.ecids)
        self.assertFalse(self.task.list('finished'))
   
    def test_finished_get_excluded(self):
        excluded = [self.ecids[0]]
        expected = [self.ecids[1]]
        self.task.finished(self.ecids)
        result = self.task.finished(exclude=excluded)
        self.assertEquals(result, expected)
        self.assertItemsEqual(self.task.list('finished'), excluded)
   
    def test_finished_get_excluded_missing(self):
        expected = self.ecids
        self.task.finished(self.ecids)
        result = self.task.finished(exclude=['missing'])
        self.assertItemsEqual(result, expected)
        self.assertItemsEqual(self.task.list('finished'), [])
   

class TestTaskListQueries(BaseTestCase):

    def test_add_query(self):
        self.task.query('isSupervised', self.ecids)
        ecids = self.task.record['isSupervised']
        self.assertItemsEqual(ecids, self.ecids)
        self.assertIn('isSupervised', self.task.record['queries'])
      
    def test_list_queries(self):
        self.task.query('isSupervised', self.ecids)
        self.task.query('name', self.ecids)
        result = self.task.queries()
        self.assertEquals(result, ['isSupervised', 'name'])

    def test_list_queries_only_missing(self):
        self.task.query('isSupervised', self.ecids)
        self.task.query('name', self.ecids)
        result = self.task.queries(only=self.only)
        self.assertEquals(result, [])
      
    def test_list_queries_exclude_all(self):
        self.task.query('isSupervised', self.ecids)
        self.task.query('name', self.ecids)
        result = self.task.queries(exclude=self.ecids)
        self.assertEquals(result, [])
      
    def test_list_queries_exclude_most(self):
        self.task.query('isSupervised', self.ecids)
        self.task.query('name', self.only)
        result = self.task.queries(exclude=self.ecids)
        self.assertEquals(result, ['name'])
      
    def test_list_queries_only_one(self):
        self.task.query('isSupervised', self.ecids)
        self.task.query('name', self.only)
        result = self.task.queries(only=self.only)
        self.assertEquals(result, ['name'])
      
    def test_list_queries_only_none(self):
        self.task.query('isSupervised', self.ecids)
        result = self.task.queries(only=self.only)
        self.assertEquals(result, [])
      
    def test_ecids_in_query(self):
        self.task.query('isSupervised', self.ecids)
        ecids = self.task.record['isSupervised']
        self.assertItemsEqual(ecids, self.ecids)

    def test_query_emptied(self):
        self.task.query('isSupervised', self.ecids)
        result = self.task.query('isSupervised')
        self.assertEquals(self.task.queries(), [])
        ecids = self.task.record['isSupervised']
        self.assertItemsEqual(ecids, [])

    def test_query_empty(self):
        self.task.query('isSupervised', [])
        self.assertFalse(self.task.queries())
        with self.assertRaises(KeyError):
            _list = self.task.record['isSupervised']

    def test_query_empty_excluded(self):
        self.task.query('isSupervised', [], exclude=['missing'])
        self.assertFalse(self.task.queries())
        with self.assertRaises(KeyError):
            _list = self.task.record['isSupervised']

    def test_query_exclude(self):
        self.task.query('isSupervised', self.ecids)
        excluded = [self.ecids[0]]
        result = self.task.query('isSupervised', exclude=excluded)
        self.assertEquals(self.task.queries(), ['isSupervised'])
        ecids = self.task.record['isSupervised']
        self.assertItemsEqual(ecids, excluded)

    def test_query_exclude_all(self):
        excluded = self.ecids
        self.task.query('isSupervised', self.ecids, excluded)
        with self.assertRaises(KeyError):
            _list = self.task.record['isSupervised']
        self.assertEquals(self.task.queries(), [])

    def test_query_exclude_missing(self):
        self.task.query('isSupervised', self.ecids)
        excluded = ['missing']
        result = self.task.query('isSupervised', exclude=excluded)
        self.assertEquals(self.task.queries(), [])
        ecids = self.task.record['isSupervised']
        self.assertEquals(ecids, [])


class TestTaskListRepeatQueries(BaseTestCase):

    def test_query_then_exclusion(self):
        excluded = [self.ecids[0]]
        self.task.query('isSupervised', self.ecids)
        result = self.task.query('isSupervised', exclude=excluded)
        self.assertEquals(result, [self.ecids[1]])
        self.task.query('isSupervised', self.ecids, exclude=excluded)
        _list = self.task.record['isSupervised']
        self.assertItemsEqual(_list, self.ecids)
      

class TestThreaded(BaseTestCase):
    '''Tests involving threading
    '''
    def setUp(self):
        super(self.__class__, self).setUp()
        self.task2 = TaskList(self.id, path=self.path)
        self.task3 = TaskList(self.id, path=self.path)
        
    def test_threaded_add_get_list_repeat(self):
        '''test threaded tasks behave as expected over several iterations
        '''                
        e1, e2 = self.ecids
        ## lambda for thread: <task obj>.add('test', [<ecid>])
        add = lambda task,ecid: task.add('test', [ecid])
        # repeat the threading several times
        for x in range(0, 5):
            # verify task is empty before starting
            self.assertFalse(self.task.list('test'))
            t1 = threading.Thread(target=add, args=(self.task2, e1))
            t2 = threading.Thread(target=add, args=(self.task3, e2))
            t1.start()
            t2.start()
            # block until the threads are finished
            t1.join()
            t2.join()
#             verify something was added to the task (also stall)
#             self.assertTrue(self.task.list('test'))
            # make sure both ECIDs are accounted for
            self.assertItemsEqual(self.task.get('test'), self.ecids)
            # make sure task is empty after get()
            self.assertFalse(self.task.list('test'))

    def test_threaded_add_duplicate_repeat(self):
        '''test threaded adding of identical items
        '''                
        e1, e2 = self.ecids
        ## lambda for thread: <task obj>.add('test', [<ecid>])
        add = lambda task,ecid: task.add('test', [ecid])
        # repeat the threading several times
        for x in range(0, 5):
            # verify task is empty before starting
            self.assertFalse(self.task.list('test'))
            t1 = threading.Thread(target=add, args=(self.task2, e1))
            t2 = threading.Thread(target=add, args=(self.task3, e1))
            t1.start()
            t2.start()
            # block until the threads are finished
            t1.join()
            t2.join()
            # verify something was added to the task (also stall)
            self.assertTrue(self.task.list('test'))
            # make sure only one item was added to the task
            self.assertItemsEqual(self.task.get('test'), [e1])
            # make sure task is empty after get()
            self.assertFalse(self.task.list('test'))


class TestLocking(BaseTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.task = TaskList(self.id, path=self.path, timeout=0)
        self.lock = FileLock(self.task.config.lockfile, 
                                      timeout=1)
        
    def test_device_locked(self):
        with self.lock.acquire():
            with self.assertRaises(Exception):
                self.task.add('erase', self.ecids[0])
        


if __name__ == '__main__':
    unittest.main(verbosity=2)

