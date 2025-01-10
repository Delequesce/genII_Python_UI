class RingBuffer:
    def __init__(self, bufsize):
        self.bufsize = bufsize
        self.data = []
    
    class __Full:
        def add(self, x):
            self.data[self.currpos] = x
            self.currpos = (self.currpos + 1) % self.bufsize

    def add(self, x):
        self.data.append(x)
        if len(self.data) == self.bufsize:
            self.currpos = 0
            self.__class__ = self.__Full