# -*- coding: utf-8 -*-

import logging
import config

'''Persistant Tasking Queue
'''

__author__ = "Sam Forester"
__email__ = "sam.forester@utah.edu"
__copyright__ = "Copyright (c) 2018 University of Utah, Marriott Library"
__license__ = "MIT"
__version__ = '2.1.2'
__url__ = None
__description__ = 'Persistant Task Queue'
__all__ = ['TaskList']

# 2.0.1:
#   - added alldone() function
# 2.1.0:
#   - added remove()
#   - modified query to remove key if empty
# 2.1.1:
#   - added (minimal) tests in test_tasklist.py
#   - removed finished, and other unused code
#   - modified default logging
# 2.1.2:
#   - modified default logging


class TaskList(object):

    def __init__(self, id, logger=None, **kwargs):
        if not logger:
            logger = logging.getLogger(__name__)
            if not logger.handlers:
                logger.addHandler(logging.NullHandler())
        self.log = logging

        self.config = config.Manager("{0}.tasks".format(id), **kwargs)
        self.file = self.config.file
        self._taskkeys = ['erase', 'prepare', 'installapps']
        try:
            self.config.read()
        except:
            _tasks = {k:[] for k in self._taskkeys}
            _tasks['queries'] = []
            self.config.write(_tasks)

    @property
    def record(self):
        '''Returns contents of config as read from disk
        '''
        return self.config.read()
    
    def get(self, key, exclude=[], only=None):
        '''Return and remove items in specified task.
        Excluded items are not returned and, if present, not removed.
        '''
        with self.config.lock.acquire():
            # get all items as set (or empty list)
            current = set(self.config.get(key, []))
            try:
                o = set(only) 
            except:
                o = set([])
            # only exclude what was there to begin with
            excluded = current.intersection(exclude)
            # what's left after removing exclusions (if any)
            left = current - excluded
            # update o from what's left (if anything)
            o = o.intersection(left)
            # if only was specified, it's what we get (even if empty)
            if only is not None:
                # remove what was taken
                self.config.update({key: list(current - o)})
                return list(o)
            if left:
                # leave behind any exclusions
                self.config.update({key: list(excluded)})
                return list(left)
            return []
    
    def list(self, key, exclude=[], only=None):
        '''Return list of items in specifed task WITHOUT removing.
        '''
        # similar logic to get() except no writing
        with self.config.lock.acquire():
            current = set(self.config.get(key, []))
            try:
                o = set(only) 
            except:
                o = set([])
            excluded = current.intersection(exclude)
            left = current - excluded
            o = o.intersection(left)
            if only is not None:
                return list(o)
            if left:
                return list(left)
            return []
     
    def add(self, key, items, exclude=[]):
        '''Add list of items to specified task, ignoring duplicates.
        '''
        with self.config.lock.acquire():
            if not isinstance(items, (list, set)):
                raise TypeError("{0}: not list or set".format(items))
            _items = set(items).difference(exclude)
            if _items:
                self.log.debug("adding: {0}: {1}".format(key, _items))
                try:
                    self.config.add(key, _items)
                except KeyError:
                    self.config.update({key: list(_items)})

    def remove(self, ecids, tasks=None, queries=None, all=False):
        '''remove specified ECID specified tasks and/or queries
        Nothing is returned
        '''
        # TO-DO: 
        #   - more tests
        #   - document
        with self.config.lock.acquire():
            if all:
                # remove all tasks associated with specified ECIDs
                for task in self._taskkeys:
                    self.get(task, only=ecids)

                for q in self.queries(only=ecids):
                    self.query(q, only=ecids)
            else:
                # remove ECID's from specified tasks
                if tasks:
                    for task in tasks:
                        self.get(task, only=ecids)
                # remove ECID's from specified queries
                if queries:
                    for q in queries:
                        self.query(q, only=ecids)
        
    def alldone(self):
        '''Returns False if any tasks need to be performed
        '''
        with self.config.lock.acquire():
            for v in self.record.values():
                if v:
                    return False
        return True
      
    def queries(self, exclude=[], only=None):
        '''Returns list of query keys
        '''
        result = []
        for k in self.list('queries'):
            if self.list(k, exclude, only):
                result.append(k)
        return result
    
    def query(self, key, ecids=[], exclude=[], only=None):
        with self.config.lock.acquire():
            if ecids:
                e = set(ecids).difference(exclude)
                self.add(key, e)
                if self.list(key):
                    self.add('queries', [key])
            else:
                ecids = self.get(key, exclude, only)
                if not self.list(key):
                    # if nothing's left, we can get rid of the query
                    try:
                        self.config.remove('queries', key)
                        self.config.remove(key)
                    except ValueError:
                        pass
                return ecids

    def erase(self, ecids=[], exclude=[], only=None):
        '''Convenience function for add('erase') and get('erase')

        task.erase(ecids, exclude=[ecid,...])
            == task.add('erase', ecids, exclude=[ecid, ...])

        task.erase(exclude=[ecid,...])
            == task.get('erase', exclude=[ecid, ...])
        '''
        with self.config.lock.acquire():
            if ecids:
                self.add('erase', ecids, exclude)
            else:
                return self.get('erase', exclude, only)

    def prepare(self, ecids=[], exclude=[], only=None):
        '''Convenience function for add('prepare') and get('prepare')

        task.prepare(ecids=[ecid, ...], exclude=[ecid,...])
            == task.add('prepare', ecids, exclude=[ecid, ...])

        task.prepare(exclude=[ecid,...])
            == task.get('prepare', exclude=[ecid, ...])
        '''
        with self.config.lock.acquire():
            if ecids:
                self.add('prepare', ecids, exclude)
            else:
                return self.get('prepare', exclude, only)

    def installapps(self, ecids=[], exclude=[], only=None):
        '''Convenience function for add('installapps') and get('installapps')

        task.installapps(ecids=[ecid, ...], exclude=[ecid,...])
            == task.add('installapps', ecids, exclude=[ecid, ...])

        task.installapps(exclude=[ecid,...])
            == task.get('installapps', exclude=[ecid, ...])
        '''
        with self.config.lock.acquire():
            if ecids:
                self.add('installapps', ecids, exclude)
            else:
                return self.get('installapps', exclude, only)


if __name__ == '__main__':
    pass
