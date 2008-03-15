from common import FuncStats
from itertools import izip
from math import sin, cos, pi
from random import shuffle
colors = ximport('colors')

size(800, 600)

DEG_TO_RAD = 2 * pi / 360
STROKE_COLOR = color(1.0, 1.0, 1.0, 0.5)
STROKE_WIDTH = 1.0
path = "/Users/mrevelle/src/cs671/topo/data"
func_stats = FuncStats.normalize(FuncStats.from_file(path))
index = FuncStats.create_index(func_stats)
root = [fn_stat for fn_stat in func_stats if (0 in fn_stat.depths)][0]

def range_subtract(a, b):
    c = (0.0, 0.0)
    if (b[0] >= 0) and (a[0] >= 0):
        c[0] = b[0] if (b[0] < a[0]) else a[0]
    elif (b[0] >= 0) and (a[0] < 0):
        c[0] = b[0]
        
def create_range(start, size):
    """start should be positive."""
    print start, size
    print ((start + size - 360), start)
    return ((start + size - 360), start)

def size_of(fnstat):
    MAX = 100
    return MAX / (min(fnstat.depths) + 1)
    
def grad_of(fnstat, x, y):
    r = 1.0 * fnstat.total_time
    g = 1.0 * 1.0 - fnstat.total_time
    b = 0.0
    a = 1.0 * (fnstat.contrib_time / fnstat.total_time)
    
    d = colors.shader(x, y, WIDTH/2, HEIGHT/2, angle=None, radius=350)    
    clr1 = color(r+d*0.5, g+d*0.3, b, a)
    clr2 = color(0, 0, 0, d)
#    return color(r, g, b, a)
    return (clr1, clr2, d, a)
    
def draw_node(fnstat):
    siz = size_of(fnstat)
    x = -siz/2
    y = -siz/2
#    fill(color_of(fnstat, x, y))
    stroke(STROKE_COLOR)
    strokewidth(STROKE_WIDTH)
    p = oval(x, y, siz, siz)
    (clr1, clr2, d, a) = grad_of(fnstat, x, y)
    colors.gradientpath(p, clr1, clr2, dx=siz/2-5, dy=siz/2-5)

def draw_graph(root, angle_range, depth):
    draw_node(root)
    min_angle = float(min(angle_range))
    max_angle = float(max(angle_range))
    angle_step = None
    num_steps = len(root.callees)    
    if len(root.callees) > 1:
        angle_step = float(max_angle - min_angle) / float(num_steps)
    elif len(root.callees) == 1:
        num_steps = 5
        angle_step = float(max_angle - min_angle) / float(num_steps)

    rand_steps = range(1, num_steps+1)
    shuffle(rand_steps)
    
    if root.name == "read":
        print rand_steps
        print root.name, angle_step, min_angle, max_angle, num_steps
    
    for i, child in izip(rand_steps, [index[name] for name in root.callees]):
        push()
        angle = (i * angle_step + min_angle) * DEG_TO_RAD
        alpha = 1 / (depth * 0.5)
        push()
        translate(size_of(root)/2*cos(angle), size_of(root)/2*-sin(angle))
        line(0, 0, cos(angle) * (60 * alpha - size_of(root)/2 - size_of(child)/2), -sin(angle) * (60 * alpha - size_of(root)/2 - size_of(child)/2))
        pop()

        translate(cos(angle) * 60 * alpha, -sin(angle) * 60 * alpha)
        
        invalid_center = (angle + 180) % 360
        valid_range = create_range((invalid_center+30), 180)
        draw_graph(child, valid_range, depth+1)
        pop()
    
def draw():
    colors.shadow(0.5)
#    background(0.1, 0.1, 0.1)
    bg = rect(0, 0, WIDTH, HEIGHT, draw=False)
    colors.gradientpath(bg, color(0.1,0.1,0.1), color(0,0,0))
    translate(WIDTH/2, HEIGHT/2)
    draw_graph(root, (0.0, 360.0), 1)
    
draw()