# -*- coding: utf-8 -*-

import logging

import config

"""
Persistant Tasking Queue
"""

__author__ = 'Sam Forester'
__email__ = 'sam.forester@utah.edu'
__copyright__ = 'Copyright(c) 2019 University of Utah, Marriott Library'
__license__ = 'MIT'
__version__ = "2.1.3"
__all__ = ['TaskList']

# suppress "No handlers could be found" message
logging.getLogger(__name__).addHandler(logging.NullHandler())

#TO-DO: move this elsewhere
def debug(fn):
    def DEBUG(*args, **kwargs):
        logger = logging.getLogger(__name__)
        lvl = logger.level if logger.level != logging.DEBUG else None
        n = fn.func_name
        logger.debug(">> %s(%r, %r)", n, args, kwargs)
        ret = fn(*args,**kwargs)
        logger.debug(">> %s(%r, %r) -> returned: %r", n, args, kwargs, ret)
        if lvl is not None:
            logger.level = lvl
        return ret
    return DEBUG


class TaskList(object):

    def __init__(self, _id, **kwargs):
        self.log = logging.getLogger(__name__)

        self.config = config.Manager("{0}.tasks".format(_id), **kwargs)
        self.file = self.config.file
        self._taskkeys = ['erase', 'prepare', 'installapps']
        try:
            self.config.read()
        except config.Missing as e:
            self.log.debug("unable to read config: %s", e)
            self.log.info("creating default task file: %r", self.file)
            _tasks = {k: [] for k in self._taskkeys}
            _tasks['queries'] = []
            self.config.write(_tasks)

    @property
    def record(self):
        """
        :returns: dict of contents as read from disk
        """
        return self.config.read()
    
    def get(self, key, exclude=(), only=None):
        """
        Retrieve tasked ECIDs (removed from)

        :param string key:      name of task
        :param exclude:         iterable of ECIDs to exclude 
                                    excluded ECIDs remain tasked (if present)
        :param only:            iterable of ECIDs to retrieve 
                                    all other ECIDs remain tasked

        :returns: list of ECIDs
        """
        with self.config.lock.acquire():
            # get all items as set (or empty list)
            current = set(self.config.get(key, []))
            try:
                o = set(only) 
            except TypeError:
                o = set()
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
    
    def list(self, key, exclude=(), only=None):
        """
        List tasked ECIDs (all ECIDs remain tasked)

        :returns: list of ECIDs
        """
        # similar logic to get() except no writing
        with self.config.lock.acquire():
            current = set(self.config.get(key, []))
            try:
                o = set(only) 
            except TypeError:
                o = set()
            excluded = current.intersection(exclude)
            left = current - excluded
            o = o.intersection(left)
            if only is not None:
                return list(o)
            if left:
                return list(left)
            return []

    @debug
    def add(self, key, items, exclude=()):
        """
        Add items to specified task

        :param string key:          name of task
        :param iterable items:      items to add
        :param iterable exclude:    ignore items (present or not)
                                
        NOTE:
            exclude is useful when working with a generic list

            # only adds (1, 2)
            >>> task.add('example', [1, 2, 3], exclude=(3, 4))

        :returns: None
        """
        if not items:
            self.log.debug("%s: nothing to add", key)
            return
        with self.config.lock.acquire():
            if not isinstance(items, (list, set)):
                self.log.error("%r: not list or set", items)
                raise TypeError("{0!r}: not list or set".format(items))
            _items = set(items).difference(exclude)
            if _items:
                self.log.debug("adding: %r: %r", key, _items)
                try:
                    self.config.add(key, _items)
                except KeyError:
                    self.config.update({key: list(_items)})

    def remove(self, ecids, tasks=None, queries=None):
        """
        Remove specified items from multiple tasks

        :param iterable items:      items to remove
        :param iterable tasks:      only remove items from specified tasks
        :param iterable queries:    keys for queries
        
        if tasks is None, then items are removed from all tasks                       
        
        :returns: None
        """
        # TO-DO: 
        #   - more tests
        #   - document
        if not ecids:
            self.log.debug("nothing specified")
            return
        with self.config.lock.acquire():
            if not tasks:
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
        
    #TO-DO: rename to 'empty' or all
    def alldone(self):
        """
        :returns: False if any items are tasked, otherwise True 
        """
        with self.config.lock.acquire():
            for v in self.record.values():
                if v:
                    return False
        return True
      
    def queries(self, exclude=(), only=None):
        """
        :returns: list of query keys
        """
        result = []
        for k in self.list('queries'):
            if self.list(k, exclude, only):
                result.append(k)
        return result
    
    def query(self, key, ecids=(), exclude=(), only=None):
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

    def erase(self, ecids=(), exclude=(), only=None):
        """
        Convenience function for add('erase') and get('erase')

        task.erase(ecids, exclude=[ecid,...])
            == task.add('erase', ecids, exclude=[ecid, ...])

        task.erase(exclude=[ecid,...])
            == task.get('erase', exclude=[ecid, ...])
        """
        with self.config.lock.acquire():
            if ecids:
                self.add('erase', ecids, exclude)
            else:
                return self.get('erase', exclude, only)

    def prepare(self, ecids=(), exclude=(), only=None):
        """
        Convenience function for add('prepare') and get('prepare')

        task.prepare(ecids=[ecid, ...], exclude=[ecid,...])
            == task.add('prepare', ecids, exclude=[ecid, ...])

        task.prepare(exclude=[ecid,...])
            == task.get('prepare', exclude=[ecid, ...])
        """
        with self.config.lock.acquire():
            if ecids:
                self.add('prepare', ecids, exclude)
            else:
                return self.get('prepare', exclude, only)

    def installapps(self, ecids=(), exclude=(), only=None):
        """
        Convenience function for add('installapps') and get('installapps')

        task.installapps(ecids=[ecid, ...], exclude=[ecid,...])
            == task.add('installapps', ecids, exclude=[ecid, ...])

        task.installapps(exclude=[ecid,...])
            == task.get('installapps', exclude=[ecid, ...])
        """
        with self.config.lock.acquire():
            if ecids:
                self.add('installapps', ecids, exclude)
            else:
                return self.get('installapps', exclude, only)


if __name__ == '__main__':
    pass
