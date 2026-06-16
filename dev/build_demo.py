"""build_demo.py - reproducible Phase 1 demo (dev harness, not shipped).

Run via the bridge:
    g = dict(globals()); exec(open(<this>).read(), g); result = g['result']

Builds /project1/p1_demo: a clock -> phase -> map chain wired from copies of the
library modules, and (if the pixel sketch is present) binds the sketch noise scroll
to the demo clock. Idempotent.

Depends on the library being built first: bootstrap.py -> sg_clock/sg_phase/sg_map.py.
Full rebuild order is in dev/README.md.
"""

import sys

BUILD = '/Users/krambuhl/Sites/aart-clock/plugins/aart-clock-td/build'
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)
import sg  # noqa: E402

NS = '/project1/aart_clock'
DEMO = '/project1/p1_demo'


def build_chain():
    """Success-criteria Chain A: sg_clock -> sg_divide -> sg_env -> sg_map.

    The clock's tempo drives sg_divide (which rides the clock's Time COMP); the divided gate
    fires sg_env; the envelope is shaped by sg_map. A clock-synced rhythmic envelope.
    """
    ns = op(NS)
    ex = op(DEMO)
    if ex:
        ex.destroy()
    demo = op('/project1').create('baseCOMP', 'p1_demo')
    demo.comment = 'Chain A: sg_clock -> sg_divide -> sg_env -> sg_map'
    demo.color = (0.2, 0.5, 0.5)
    demo.nodeX, demo.nodeY = -300, -700

    def cp(name, x, y):
        n = demo.copy(ns.op(name)) or demo.op(name)
        n.nodeX, n.nodeY = x, y
        return n

    clk = cp('sg_clock', -1000, 0)
    clk.par.opshortcut = 'clock'   # op.clock -> the module (params)

    # clock bus: short, direct-indexable channel handle -> op('/project1/clk')['beat']
    bus = op('/project1/clk') or op('/project1').create('selectCHOP', 'clk')
    bus.par.chop = clk.path + '/out1'
    bus.par.channames = '*'
    bus.nodeX, bus.nodeY = 0, 250
    bus.color = (0.55, 0.3, 0.3)
    bus.comment = 'clock bus - op("/project1/clk")["beat"]'

    div = cp('sg_divide', -550, 0)
    div.par.Clock = '../sg_clock'        # sibling clock in the demo
    div.par.Division = 1
    env = cp('sg_env', -100, 0)
    env.par.Mode = 'ad'                   # percussive: attack+decay per gate, ignores gate length
    env.par.Attack = 0.01
    env.par.Decay = 0.4
    env.par.Sustain = 0.0
    mp = cp('sg_map', 350, 0)
    mp.par.Outlow, mp.par.Outhigh = 0.0, 1.0

    # divide gate -> env trigger
    s1 = demo.create('selectCHOP', 'pick_gate')
    s1.nodeX, s1.nodeY = -320, -170
    s1.par.chop = div.path + '/out1'
    s1.par.channames = 'gate'
    s1.outputConnectors[0].connect(env.inputConnectors[0])

    # env -> map
    s2 = demo.create('selectCHOP', 'pick_env')
    s2.nodeX, s2.nodeY = 130, -170
    s2.par.chop = env.path + '/out1'
    s2.par.channames = 'env'
    s2.outputConnectors[0].connect(mp.inputConnectors[0])

    return demo, clk, env, mp


def bind_sketch_noise(clk):
    """Drive the pixel sketch's noiseTOP scroll from the demo clock. Guarded + dev-only.

    Replaces the sketch's stock `tz = absTime.seconds*...` with clock-continuous-beats so the
    motion is tempo-locked, and clears any parallel t4d driver. No-op if the sketch isn't present.
    """
    content = op('/project1/content')
    if not content:
        return False
    # use the short clock-bus handle (op('/project1/clk')) instead of the full module path
    content.par.tz.expr = "(op('/project1/clk')['beat'] + op('/project1/clk')['phase_beat']) * 0.025"
    # clear a stray parallel driver on t4d (reset to constant via a known-constant par's mode)
    if content.par.t4d.expr:
        content.par.t4d.mode = content.par.tx.mode
        content.par.t4d.val = 0
    return True


def run():
    demo, clk, env, mp = build_chain()
    bound = bind_sketch_noise(clk)
    content = op('/project1/content')
    return {
        'demo': demo.path,
        'nodes': sorted(c.name for c in demo.children),
        'map_value': round(float(mp.op('out1')['value'].eval()), 3),
        'noise_bound': bound,
        'noise_tz_expr': content.par.tz.expr if content else None,
        'abstime_left': {p.name: p.expr for p in content.pars() if p.expr and 'abstime' in p.expr.lower()} if content else {},
        'errors': sg.errors(demo),
    }


result = run()
