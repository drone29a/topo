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
        return "FuncStats('%s', %s, %s, %s, %s, %s, %s)" % (
            self.name, 
            self.total_time, 
            self.contrib_time, 
            self.depths, 
            self.call_count, 
            self.callers, 
            self.callees)

    @staticmethod
    def from_file(path):
        result_file = file(path, 'r')
        lines = result_file.readlines()
        result_file.close()
    
        fnstats = [eval(l) for l in lines]
        return fnstats
    
    @staticmethod
    def create_index(fnstats):
        pairs = [(fnstat.name, fnstat) for fnstat in fnstats]
        return dict(pairs)

    @staticmethod
    def normalize(fnstats):
        """Normalize the total_time, contrib_time, and call_count attributes 
        of a set of FuncStat objects."""
        
        total_time_sum = sum((fnstat.contrib_time for fnstat in fnstats))
        contrib_time_sum = sum((fnstat.contrib_time for fnstat in fnstats))
        call_count_sum = sum((fnstat.call_count for fnstat in fnstats))

        norm_fnstats = []
        for fnstat in fnstats:
            fnstat.total_time = float(fnstat.total_time) / float(total_time_sum)
            fnstat.contrib_time = float(fnstat.contrib_time) / float(contrib_time_sum)
            fnstat.call_count = float(fnstat.call_count) / float(call_count_sum)
            norm_fnstats.append(fnstat)

        return norm_fnstats
        
