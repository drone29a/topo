import sys, os
import subprocess
from itertools import groupby
from tempfile import NamedTemporaryFile, mkstemp
from subprocess import Popen
from string import Template
from optparse import OptionParser
from common import FuncStats

dtrace_tmpl = Template("""
#!/usr/sbin/dtrace -s

#pragma D option defaultargs

typedef struct {
    string func_name;  /* name of function */
    int thread_id;  /* id of running thread */
    int run_id;  /* unique run id */
    int call_id;  /* unique wrt other call_infos in this run, this orders calls */
    int depth;  /* depth in the call stack */
    uint64_t start_time;  
    uint64_t total_time;
} call_info;

self int depth;  /* current depth for each run */
self int call_id_count;  /* equivalent to a count of function entries within a run */
self int curr_call_id;  /* id of func call currently being executed by thread */
self int call_stack[int];  /* temp storage for call ids in a run */
self int stack_top;  /* top of the call stack */

int run_id_count;  /* keep track of the run id to assign new runs */

string fn;  /* name of function to trace */
int num_runs;  /* number of runs to collect */

call_info call_infos[int, int];  /* all call infos indexed by run and call id */

BEGIN
{
   run_id_count = 0;
   num_runs = $num_runs;
}

fbt:$module:$func:entry
{
  self->call_id_count = 0;
  self->rid = run_id_count;
  self->stack_top = 0;

  this->cid = self->call_id_count;
  self->depth = 0;
  this->start_time = timestamp;

  call_infos[self->rid, this->cid].func_name = probefunc;
  call_infos[self->rid, this->cid].thread_id = tid;
  call_infos[self->rid, this->cid].run_id = self->rid;
  call_infos[self->rid, this->cid].call_id = this->cid;
  call_infos[self->rid, this->cid].depth = self->depth;
  call_infos[self->rid, this->cid].start_time = this->start_time;

  self->curr_call_id = this->cid;
  self->call_stack[self->stack_top] = this->cid;

  printf("%s %d %d %d %d %d\\n", probefunc, self->rid, this->cid, tid, self->depth, this->start_time);

  ++(self->depth);
  self->curr_call_id = ++(self->call_id_count);
  ++run_id_count;
  self->in = 1;
}

fbt:::entry
/self->in && probefunc != "$func"/
{
  this->cid = self->curr_call_id;
  this->start_time = timestamp;

  call_infos[self->rid, this->cid].func_name = probefunc;
  call_infos[self->rid, this->cid].thread_id = tid;
  call_infos[self->rid, this->cid].run_id = self->rid;
  call_infos[self->rid, this->cid].call_id = this->cid;
  call_infos[self->rid, this->cid].depth = self->depth;
  call_infos[self->rid, this->cid].start_time = this->start_time;
  
  self->call_stack[++(self->stack_top)] = this->cid;

  printf("%s %d %d %d %d %d\\n", probefunc, self->rid, this->cid, tid, self->depth, this->start_time);

  ++(self->depth);
  self->curr_call_id = ++(self->call_id_count);
}

fbt:::return
/self->in && probefunc != "$func"/
{
  --(self->depth);

  this->cid = self->call_stack[self->stack_top];
  this->end_time = timestamp;
  this->start_time = call_infos[self->rid, this->cid].start_time;

  call_infos[self->rid, this->cid].total_time = this->end_time - this->start_time;

  --(self->stack_top);
  printf("%s %d %d %d\\n", probefunc, self->rid, this->cid, call_infos[self->rid, this->cid].total_time);
}

fbt:$module:$func:return
/self->in && num_runs-1 == 0/
{
  this->cid = self->call_stack[self->stack_top];
  this->end_time = timestamp;
  this->start_time = call_infos[self->rid, this->cid].start_time;

  call_infos[self->rid, this->cid].total_time = this->end_time - this->start_time;

  --(self->stack_top);
  printf("%s, %d %d %d\\n", probefunc, self->rid, this->cid, call_infos[self->rid, this->cid].total_time);

  exit(1);
}

fbt:$module:$func:return
/self->in/
{
  this->cid = self->call_stack[self->stack_top];
  this->end_time = timestamp;
  this->start_time = call_infos[self->rid, this->cid].start_time;

  call_infos[self->rid, this->cid].total_time = this->end_time - this->start_time;

  --(self->stack_top);

  printf("%s %d %d %d\\n", probefunc, self->rid, this->cid, call_infos[self->rid, this->cid].total_time);

  self->in = 0;
  --num_runs;
}
""")

class Node(object):
    def __init__(self, name, run_id, call_id, thread_id, depth, start_time, total_time, parent=None):
        self.name = name
        self.run_id = run_id
        self.call_id = call_id
        self.thread_id = thread_id
        self.depth = depth
        self.start_time = start_time
        self.total_time = total_time
        self.parent = parent
        self.children = []

    def __str__(self):
        parent_id = self.parent.call_id if self.parent else None
        return "name: %s, run_id: %s, call_id: %s, thread_id: %s, depth: %s, start_time: %s, total_time: %s, parent: %s" % (self.name, self.run_id, self.call_id, self.thread_id, self.depth, self.start_time, self.total_time, parent_id)
    
    @staticmethod
    def from_strings(args):
        for i in range(1, 7):
            args[i] = int(args[i])
        return Node(*args)

class RunTree(object):
    def __init__(self, root):
        self.run_id = root.run_id
        self.root = root

    def preorder_map(self, fn):
        result = []
        
        def descent(fn, node):
            result.append(fn(node))
            for child in node.children:
                descent(fn, child)

        descent(fn, self.root)
        return result

    def postorder_map(self, fn):
        result = []

        def descent(fn, node):
            for child in node.children:
                descent(fn, child)
            result.append(fn(node))

        descent(fn, self.root)
        return result

    def stats(self):
        def create_stat(node):
            contrib_time = node.total_time - sum([child.total_time for child in node.children], 0)
            return FuncStats(node.name, node.total_time, contrib_time, [node.depth], 1, 
                             [node.parent.name] if node.parent else [], 
                             [child.name for child in node.children])

        fn_stats = self.preorder_map(create_stat)

        grouped_stats = {}
        for fn_stat in fn_stats:
            if fn_stat.name in grouped_stats:
                grouped_stats[fn_stat.name] = grouped_stats[fn_stat.name].merge(fn_stat)
            else:
                grouped_stats[fn_stat.name] = fn_stat

        return grouped_stats.values()

    def __str__(self):
        def format_node(node):
            return "|%s> %s\n" % ("___" * node.depth, node.name)
            
        return ''.join(self.preorder_map(format_node))
                

    @staticmethod
    def build(vals):
        """Build a RunTree from input lines."""
        def comp(lx, ly):
            if len(lx) != len(ly) and lx[2] == ly[2]:
                return len(ly) - len(lx)
            else:
                return int(lx[2]) - int(ly[2])
                
        vals.sort(comp)

        root = None
        nodes = []
        for k, val in groupby(vals, lambda x: x[1:3]):
            val_lists = list(val)
            args = val_lists[0]
            args.append(val_lists[1][-1])
            node = Node.from_strings(args)
            if node.call_id == 0:
                root = node
                nodes.append(node)
            else:
                while nodes[-1].depth >= node.depth:
                    nodes.pop()
                
                node.parent = nodes[-1]
                nodes[-1].children.append(node)
                
                nodes.append(node)
                
        return RunTree(root)
 
def main(argv=None):
    if argv == None:
        argv = sys.argv

    parser = OptionParser()
    parser.add_option("-m", "--module", dest="module", default="",
                      help="module of function", metavar="MODULE")
    parser.add_option("-n", dest="num_runs", default="1",
                      help="number of runs", metavar="NUM_RUNS")
    parser.add_option("-o", "--output", dest="output_type", default="human",
                      help="type of output", metavar="TYPE")
    (options, args) = parser.parse_args(argv[1:])

    func = args[0]

    dtrace_code = dtrace_tmpl.substitute({"func": func, 
                                          "num_runs": options.num_runs,
                                          "module": options.module})

    (id, abs_path) = mkstemp()
    handle = file(abs_path, 'w')
    handle.write(dtrace_code)
    handle.close()

    cmd = Popen(["/usr/sbin/dtrace", "-s", abs_path, "-q"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = cmd.communicate()[0]
    os.remove(abs_path)

    line_vals = [line.split() for line in out.splitlines() if len(line) > 0]
    def comp(x, y):
        return int(x[1]) - int(y[1])
    line_vals.sort(comp)

    trees = []
    for k, g in groupby(line_vals, lambda x: x[1]):
        tree = RunTree.build(list(g))
        trees.append(tree)
    
    tree_stats = [tree.stats() for tree in trees]
    tree_stats = reduce(lambda x, y: x + y, tree_stats, [])

    def comp(x, y):
        return cmp(x.name, y.name)
    tree_stats.sort(comp)
    
    merged_stats = []
    for k, g in groupby(tree_stats, lambda x: x.name):
        merged = reduce(lambda x, y: x.merge(y), g)
        merged_stats.append(merged)

    def comp(x, y):
        return cmp(sum(x.depths)/len(x.depths), sum(y.depths)/len(y.depths))
    merged_stats.sort(comp)

    if options.output_type == "machine":
        for stats in merged_stats:
            print repr(stats)
    else:
        for stats in merged_stats:
            print stats

if __name__ == "__main__":
    sys.exit(main())
