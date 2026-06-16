"""sg_lfo.py - continuous periodic oscillator.

Run via the bridge:
    g = dict(globals()); exec(open(<this>).read(), g); result = g['result']

Builds /project1/aart_clock/sg_lfo. A periodic LFO (sine/triangle/saw/square) with a phase +
wrap pulse, a unipolar/bipolar Polarity convention, and a reset input for clock-sync (same seam
as sg_phase). Idempotent. Uses the sg build-helper.

DESIGN NOTE: periodic shapes only. Random Hold / Random Smooth (listed under sg_lfo in the
original plan) are RANDOM sources - sg_random owns them, to avoid duplicating the random concern
across two modules. For random modulation, patch sg_random -> sg_map.

Input (in1): a pulse to reset/align the phase (e.g. sg_clock pulse_bar). Free-running if unwired.
Params: Shape (sine/triangle/saw/square), Rate (Hz), Offset (0..1), Polarity (unipolar/bipolar),
Synctoinput. Outputs: value (in the Polarity range), phase (0..1), pulse_wrap.
"""

import sys

BUILD = '/Users/krambuhl/Sites/aart-clock/plugins/aart-clock-td/build'
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)
import sg  # noqa: E402

NS = '/project1/aart_clock'
MOD = NS + '/sg_lfo'


def build():
    c = sg.module(NS, 'sg_lfo', comment='periodic oscillator (sine/tri/saw/square)',
                  tags=('aart-clock', 'generation'), color=(0.35, 0.45, 0.6))
    page = next(p for p in c.customPages if p.name == 'Aartclock')
    page.appendMenu('Shape')
    c.par.Shape.menuNames = ['sine', 'triangle', 'saw', 'square']
    c.par.Shape.menuLabels = ['Sine', 'Triangle', 'Saw', 'Square']
    c.par.Shape.default = 'sine'
    c.par.Shape.val = 'sine'
    sg.pfloat(c, 'Rate', 1.0, 0.0, 10.0, label='Rate (Hz)')
    sg.pfloat(c, 'Offset', 0.0, 0.0, 1.0)
    page.appendMenu('Polarity')
    c.par.Polarity.menuNames = ['unipolar', 'bipolar']
    c.par.Polarity.menuLabels = ['Unipolar (0..1)', 'Bipolar (-1..1)']
    c.par.Polarity.default = 'bipolar'
    c.par.Polarity.val = 'bipolar'
    sg.ptoggle(c, 'Synctoinput', True, label='Sync To Input')

    in1 = sg.inchop(c, 'in1')
    reset_expr = "1 if (parent().par.Synctoinput and op('in1').numChans and op('in1')[0] > 0.5) else 0"

    # phase + wrap (same as sg_phase) so the LFO carries the contract channels
    ramp = c.create('lfoCHOP', 'ramp_lfo')
    ramp.par.wavetype = 'ramp'
    ramp.par.frequency.expr = 'parent().par.Rate'
    ramp.par.phase.expr = 'parent().par.Offset'
    ramp.par.channelname = 'phase'
    ramp.par.reset.expr = reset_expr

    wrap = c.create('lfoCHOP', 'wrap_lfo')
    wrap.par.wavetype = 'pulse'
    wrap.par.frequency.expr = 'parent().par.Rate'
    wrap.par.phase.expr = 'parent().par.Offset'
    wrap.par.channelname = 'pulse_wrap'
    wrap.par.reset.expr = reset_expr

    # the shaped waveform, normalized to bipolar -1..1 (saw is 0..1 natively -> amp2/offset-1)
    wave = c.create('lfoCHOP', 'wave_lfo')
    wave.par.wavetype.expr = (
        "{'sine':'sin','triangle':'tri','saw':'ramp','square':'square'}"
        ".get(parent().par.Shape.eval(), 'sin')"
    )
    wave.par.frequency.expr = 'parent().par.Rate'
    wave.par.phase.expr = 'parent().par.Offset'
    wave.par.amp.expr = "2 if parent().par.Shape.eval() == 'saw' else 1"
    wave.par.offset.expr = "-1 if parent().par.Shape.eval() == 'saw' else 0"
    wave.par.channelname = 'value'
    wave.par.reset.expr = reset_expr

    # polarity: source is -1..1; unipolar remaps to 0..1, bipolar passes through
    pol = c.create('mathCHOP', 'polarity')
    wave.outputConnectors[0].connect(pol.inputConnectors[0])
    pol.par.fromrange1, pol.par.fromrange2 = -1, 1
    pol.par.torange1.expr = "0 if parent().par.Polarity.eval() == 'unipolar' else -1"
    pol.par.torange2 = 1

    merge = sg.merge(c, 'internal', [pol, ramp, wrap])
    out1 = sg.out(c, merge)
    sg.help(c, 'sg_lfo - periodic oscillator. Shapes sine/triangle/saw/square. value (Polarity '
               'range), phase (0..1), pulse_wrap. Reset input syncs to a clock pulse. For random '
               'modulation use sg_random.\n')
    sg.arrange(c)
    return c, out1


def verify(c, out1):
    chans = sorted(ch.name for ch in out1.chans())
    checks = []
    for shape in ('sine', 'triangle', 'saw', 'square'):
        for pol, lo, hi in (('bipolar', -1.0, 1.0), ('unipolar', 0.0, 1.0)):
            c.par.Shape = shape
            c.par.Polarity = pol
            v = float(out1['value'].eval())
            checks.append({'shape': shape, 'pol': pol, 'val': round(v, 3),
                           'in_range': lo - 0.05 <= v <= hi + 0.05})
    c.par.Shape = 'sine'
    c.par.Polarity = 'bipolar'
    return {
        'module': c.path,
        'out_channels': chans,
        'has_contract': set(['value', 'phase', 'pulse_wrap']).issubset(set(chans)),
        'all_in_range': all(x['in_range'] for x in checks),
        'checks': checks,
        'params': [p.name for p in c.customPars],
        'errors': sg.errors(c),
    }


c, out1 = build()
import sys as _sys
_bp = '/Users/krambuhl/Sites/aart-clock/plugins/aart-clock-td/build'
if _bp not in _sys.path:
    _sys.path.insert(0, _bp)
import sg as _sg
_sg.arrange(c)
result = verify(c, out1)
