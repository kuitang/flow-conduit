# from http://code.activestate.com/recipes/577187-python-thread-pool/
import sys
from Queue import Queue
from threading import Thread

class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, args, kwargs, callback = self.tasks.get()
            callback(func(*args, **kwargs))
            print >> sys.stderr, "Worker: the callback %s returned."%(callback.__name__)
#            try: callback(func(*args, **kwargs))
#            except Exception as e: print e
            self.tasks.task_done()

class ThreadPool(object):
    """Pool of threads consuming tasks from a queue"""
    def __init__(self, num_threads):
        self.tasks = Queue()
        for _ in xrange(num_threads): Worker(self.tasks)

    def add_task(self, func, args, kwargs={}, callback=lambda x: x):
#        print >> sys.stderr, "add_task: ", locals()
        self.tasks.put((func, args, kwargs, callback))

    def wait_completion(self):
        self.tasks.join()

