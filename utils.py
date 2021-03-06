import torch
import torch.multiprocessing as mp
import threading

class AtomicInteger:
    def __init__(self):
        self.val = 0
        self.lock = threading.Lock()
    
    def getVal(self):
        return self.val

    def setVal(self,val):
        self.lock.acquire()
        self.val = val
        self.lock.release()

    def inc(self):
        self.lock.acquire()
        self.val += 1
        self.lock.release()

class TrafficLight:
    """used by chief to allow workers to run or not"""

    def __init__(self, val=True):
        self.val = mp.Value("b", False)
        self.lock = mp.Lock()

    def get(self):
        with self.lock:
            return self.val.value

    def switch(self):
        with self.lock:
            self.val.value = (not self.val.value)

class Counter:
    """enable the chief to access worker's total number of updates"""

    def __init__(self, val=True):
        self.val = mp.Value("i", 0)
        self.lock = mp.Lock()

    def get(self):
        # used by chief
        with self.lock:
            return self.val.value

    def increment(self):
        # used by workers
        with self.lock:
            self.val.value += 1

    def reset(self):
        # used by chief
        with self.lock:
            self.val.value = 0
