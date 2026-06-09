"""sg_divide.py - clock division / multiplication.

Run via the bridge:
    g = dict(globals()); exec(open(<this>).read(), g); result = g['result']

Builds /project1/aart_clock/sg_divide. Rides the clock's Time COMP (via the Clock path
param) at a scaled period, so the divided phase is automatically aligned to the clock - no
reset wiring needed. Idempotent. Uses the sg build-helper.

Params: Clock (path to the sg_clock module, default ../sg_clock), Division, Multiplication,
Offset (beats), Gatewidth. Outputs: phase (0..1 at the divided rate), gate (0/1), pulse.
NOTE (v1): Swing deferred - Beat CHOP doesn't express uneven swing as one param (PLAN risk).
"""

import sys

BUILD = '/Users/krambuhl/Sites/aart-clock/plugins/aart-clock-td/build'
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)
import sg  # noqa: E402

NS = '/project1/aart_clock'
MOD = NS + '/sg_divide'


def build():
    c = sg.module(NS, 'sg_divide', comment='clock division / multiplication',
                  tags=('aart-clock', 'timing'), color=(0.55, 0.4, 0.3))
    # params
    page = next(p for p in c.customPages if p.name == 'Aartclock')
    page.appendStr('Clock')
    c.par.Clock.default = '../sg_clock'
    c.par.Clock.val = '../sg_clock'
    sg.pint(c, 'Division', 1)
    sg.pint(c, 'Multiplication', 1)
    sg.pfloat(c, 'Offset', 0.0, label='Offset (beats)')
    sg.pfloat(c, 'Gatewidth', 0.5, 0.0, 1.0, label='Gate Width')

    # Beat CHOP riding the referenced clock's Time COMP at a scaled period
    beat = c.create('beatCHOP', 'beat')
    beat.par.op.expr = "parent().par.Clock.eval() + '/local_time'"
    beat.par.period.expr = "parent().par.Division / max(1, parent().par.Multiplication)"
    beat.par.shiftoffset.expr = "parent().par.Offset"
    for on in ('ramp', 'pulse', 'count'):
        setattr(beat.par, on, True)
    for off in ('sine', 'countramp', 'bar', 'beat'):
        if hasattr(beat.par, off):
            setattr(beat.par, off, False)

    # rename to the contract (ramp->phase); keep pulse; drop the counter downstream
    rn = sg.rename(c, 'rename', beat, 'ramp pulse count', 'phase pulse pcount')

    # gate = phase within [0, Gatewidth]  (Logic CHOP bound conversion)
    sel_p = c.create('selectCHOP', 'sel_phase')
    sel_p.par.chop = 'rename'          # relative -> copy-safe
    sel_p.par.channames = 'phase'
    lg = c.create('logicCHOP', 'gate_logic')
    sel_p.outputConnectors[0].connect(lg.inputConnectors[0])
    lg.par.convert = 'bound'
    lg.par.boundmin = 0.0
    lg.par.boundmax.expr = 'parent().par.Gatewidth'
    rg = sg.rename(c, 'name_gate', lg, 'phase', 'gate')

    # main path: phase + pulse
    sel_m = c.create('selectCHOP', 'sel_main')
    sel_m.par.chop = 'rename'
    sel_m.par.channames = 'phase pulse'

    merge = sg.merge(c, 'internal', [sel_m, rg])
    out1 = sg.out(c, merge)
    sg.help(c, 'sg_divide - divide/multiply a clock. Clock param -> the sg_clock module. '
               'Outputs phase (divided 0..1), gate (0/1), pulse.\n')
    sg.arrange(c)
    return c, out1


def verify(c, out1):
    chans = sorted(ch.name for ch in out1.chans())
    vals = {n: round(float(out1[n].eval()), 4) for n in chans}
    phase = vals.get('phase')
    gate = vals.get('gate')
    gate_consistent = None
    if phase is not None and gate is not None:
        expected_gate = 1.0 if phase < float(c.par.Gatewidth.eval()) else 0.0
        gate_consistent = abs(gate - expected_gate) < 0.5
    return {
        'module': c.path,
        'out_channels': chans,
        'has_contract': set(['phase', 'gate', 'pulse']).issubset(set(chans)),
        'vals': vals,
        'phase_in_range': (phase is None) or (0.0 <= phase < 1.0001),
        'gate_is_binary': (gate is None) or (gate in (0.0, 1.0)),
        'gate_matches_phase': gate_consistent,
        'params': [p.name for p in c.customPars],
        'errors': sg.errors(c),
    }


c, out1 = build()
result = verify(c, out1)
