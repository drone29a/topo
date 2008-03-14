class FuncStats(object):
    def __init__(self, name, total_time, contrib_time, depths, call_count, callers, callees):
        self.name = name
        self.total_time = total_time
        self.contrib_time = contrib_time
        self.depths = depths
        self.call_count = call_count
        self.callers = callers
        self.callees = callees

    def merge(self, other):
        if self.name == other.name:
            args = (self.name,
                    self.total_time + other.total_time,
                    self.contrib_time + other.contrib_time,
                    self.depths + other.depths,
                    self.call_count + other.call_count,
                    list(set(self.callers + other.callers)),
                    list(set(self.callees + other.callees)))
            return FuncStats(*args)

    def __str__(self):
        return "%s, total time: %s, contrib time: %s, depths: %s, call count: %s, callers: %s, callees: %s" % (
            self.name,
            self.total_time, 
            self.contrib_time, 
            self.depths, 
            self.call_count, 
            self.callers, 
            self.callees)

    def __repr__(self):
        return "FuncStats(%s, %s, %s, %s, %s, %s, %s)" % (
            self.name, 
            self.total_time, 
            self.contrib_time, 
            self.depths, 
            self.call_count, 
            self.callers, 
            self.callees)
