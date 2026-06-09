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
    ns = op(NS)
    ex = op(DEMO)
    if ex:
        ex.destroy()
    demo = op('/project1').create('baseCOMP', 'p1_demo')
    demo.comment = 'Phase 1 chain demo: sg_clock -> sg_phase -> sg_map'
    demo.color = (0.2, 0.5, 0.5)
    demo.nodeX, demo.nodeY = -300, -700

    def cp(name, x, y):
        n = demo.copy(ns.op(name)) or demo.op(name)
        n.nodeX, n.nodeY = x, y
        return n

    clk = cp('sg_clock', -800, 0)
    ph = cp('sg_phase', -350, 0)
    ph.par.Rate = 0.5                       # one sweep per bar @120bpm
    mp = cp('sg_map', 200, 0)
    mp.par.Outlow, mp.par.Outhigh = 0, 360  # e.g. a rotation range

    # clock pulse_bar -> phase reset input (locks phase to the bar)
    s1 = demo.create('selectCHOP', 'pick_pulse_bar')
    s1.nodeX, s1.nodeY = -570, -170
    s1.par.chop = clk.path + '/out1'
    s1.par.channames = 'pulse_bar'
    s1.outputConnectors[0].connect(ph.inputConnectors[0])

    # phase -> map
    s2 = demo.create('selectCHOP', 'pick_phase')
    s2.nodeX, s2.nodeY = -90, -170
    s2.par.chop = ph.path + '/out1'
    s2.par.channames = 'phase'
    s2.outputConnectors[0].connect(mp.inputConnectors[0])

    return demo, clk, ph, mp


def bind_sketch_noise(clk):
    """Drive the pixel sketch's noiseTOP scroll from the demo clock. Guarded + dev-only.

    Replaces the sketch's stock `tz = absTime.seconds*...` with clock-continuous-beats so the
    motion is tempo-locked, and clears any parallel t4d driver. No-op if the sketch isn't present.
    """
    content = op('/project1/content')
    if not content:
        return False
    co = clk.path + '/out1'
    content.par.tz.expr = "(op('%s')['beat'] + op('%s')['phase_beat']) * 0.025" % (co, co)
    # clear a stray parallel driver on t4d (reset to constant via a known-constant par's mode)
    if content.par.t4d.expr:
        content.par.t4d.mode = content.par.tx.mode
        content.par.t4d.val = 0
    return True


def run():
    demo, clk, ph, mp = build_chain()
    bound = bind_sketch_noise(clk)
    content = op('/project1/content')
    return {
        'demo': demo.path,
        'nodes': sorted(c.name for c in demo.children),
        'map_value_deg': round(float(mp.op('out1')['value'].eval()), 1),
        'noise_bound': bound,
        'noise_tz_expr': content.par.tz.expr if content else None,
        'abstime_left': {p.name: p.expr for p in content.pars() if p.expr and 'abstime' in p.expr.lower()} if content else {},
        'errors': sg.errors(demo),
    }


result = run()
