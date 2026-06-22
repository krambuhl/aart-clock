"""strobe-bar.py — generated aart-clock program (dev harness, not shipped).

Description: a punchy strobe on every bar
Chain: sg_clock -> sg_divide -> sg_env -> sg_map

A once-per-bar gate (sg_divide, Division=4 beats = 1 bar) fires a percussive AD
envelope (fast attack, short decay — the "punch"), shaped to 0..1 by sg_map. The
output is a sharp flash-shaped Value spiking once per bar.

Run via the bridge:
    g = dict(globals()); exec(open(<this>).read(), g); result = g['result']
Idempotent: destroys and rebuilds /project1/strobe-bar.
"""

import sys
BUILD = '/Users/krambuhl/Sites/aart-clock/plugins/aart-clock-td/build'
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)
import sg  # noqa: E402

NS = '/project1/aart_clock'
NAME = 'strobe_bar'   # TD node names can't contain dashes; file slug stays kebab
PROG = '/project1/' + NAME

BPM = 120
DIVISION = 4      # beats per gate; at Barbeats=4 -> one gate per bar


def build():
    ns = op(NS)
    if op(PROG):
        op(PROG).destroy()
    prog = op('/project1').create('baseCOMP', NAME)
    prog.comment = 'a punchy strobe on every bar | sg_clock -> sg_divide -> sg_env -> sg_map'
    prog.color = (0.2, 0.5, 0.5)

    def cp(modname, x, y):
        n = prog.copy(ns.op(modname)) or prog.op(modname)
        n.nodeX, n.nodeY = x, y
        return n

    # --- clock: the transport ---
    clk = cp('sg_clock', -1000, 0)
    clk.par.Bpm = BPM
    clk.par.Play = True

    # --- divide: one gate per bar (4 beats) ---
    div = cp('sg_divide', -550, 0)
    div.par.Clock = '../sg_clock'   # sibling clock in this container
    div.par.Division = DIVISION
    div.par.Gatewidth = 0.1         # short gate; AD env ignores length, only needs the edge

    # --- env: the punch (AD = attack then decay to zero, per trigger) ---
    env = cp('sg_env', -100, 0)
    env.par.Mode = 'ad'
    env.par.Attack = 0.005          # near-instant rise
    env.par.Decay = 0.08            # fast fall -> snappy strobe
    env.par.Sustain = 0.0

    # --- map: normalize to 0..1 ---
    mp = cp('sg_map', 350, 0)
    mp.par.Outlow, mp.par.Outhigh = 0.0, 1.0

    # divide gate -> env trigger
    s1 = prog.create('selectCHOP', 'pick_gate')
    s1.par.chop = div.path + '/out1'
    s1.par.channames = 'gate'
    s1.outputConnectors[0].connect(env.inputConnectors[0])

    # env -> map
    s2 = prog.create('selectCHOP', 'pick_env')
    s2.par.chop = env.path + '/out1'
    s2.par.channames = 'env'
    s2.outputConnectors[0].connect(mp.inputConnectors[0])

    out_src = mp.op('out1')

    # --- output bus + trail (always) ---
    bus = op(PROG + '_bus') or op('/project1').create('selectCHOP', NAME + '_bus')
    bus.par.chop = out_src.path
    bus.par.channames = '*'
    bus.nodeX, bus.nodeY = 600, 250
    bus.color = (0.55, 0.3, 0.3)
    bus.comment = "program bus - op('%s_bus')['value']" % PROG
    trail = prog.create('trailCHOP', 'trail1')
    out_src.outputConnectors[0].connect(trail.inputConnectors[0])

    sg.arrange(prog)
    return prog, div, mp, out_src


def run():
    prog, div, mp, out_src = build()
    return {
        'program': prog.path,
        'nodes': sorted(c.name for c in prog.children),
        # deterministic assertions:
        'division_beats': float(div.par.Division.eval()),   # expect 4.0 -> one gate per bar
        'out_range': [float(mp.par.Outlow.eval()), float(mp.par.Outhigh.eval())],
        'out_channels': out_src.chanNames if hasattr(out_src, 'chanNames') else [c.name for c in out_src.chans()],
        # feel — note, don't fake an assertion:
        'feel': 'eyeball strobe contour on trail1: sharp spike to 1, ~0.08s decay, once per bar',
        'bus': prog.path + '_bus',
        'errors': sg.errors(prog),
    }


result = run()
