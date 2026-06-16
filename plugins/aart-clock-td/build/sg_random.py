"""sg_random.py - randomized signal source.

Run via the bridge:
    g = dict(globals()); exec(open(<this>).read(), g); result = g['result']

Builds /project1/aart_clock/sg_random. Noise-CHOP-based random sources with a deterministic Seed
and a Rate-controlled variation speed, output on the Polarity convention. Idempotent. sg helper.

Modes: White Noise (uncorrelated), Random Walk (brownian, 1 integral), Brownian (smoother walk).
Params: Mode, Seed, Rate (Hz), Polarity. Output: value (Polarity range).
NOTE (v1): Chaos deferred - it needs a stateful Python logistic map (no native CHOP), same as the
swing deferral in sg_divide. White/Walk/Brownian cover the common cases.
"""

import sys

BUILD = '/Users/krambuhl/Sites/aart-clock/plugins/aart-clock-td/build'
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)
import sg  # noqa: E402

NS = '/project1/aart_clock'
MOD = NS + '/sg_random'


def build():
    c = sg.module(NS, 'sg_random', comment='randomized source (noise / walk / brownian)',
                  tags=('aart-clock', 'generation'), color=(0.4, 0.5, 0.55))
    page = next(p for p in c.customPages if p.name == 'Aartclock')
    page.appendMenu('Mode')
    c.par.Mode.menuNames = ['whitenoise', 'randomwalk', 'brownian']
    c.par.Mode.menuLabels = ['White Noise', 'Random Walk', 'Brownian']
    c.par.Mode.default = 'whitenoise'
    c.par.Mode.val = 'whitenoise'
    sg.pint(c, 'Seed', 1)
    sg.pfloat(c, 'Rate', 2.0, 0.0, 20.0, label='Rate (Hz)')
    page.appendMenu('Polarity')
    c.par.Polarity.menuNames = ['unipolar', 'bipolar']
    c.par.Polarity.menuLabels = ['Unipolar (0..1)', 'Bipolar (-1..1)']
    c.par.Polarity.default = 'bipolar'
    c.par.Polarity.val = 'bipolar'

    nz = c.create('noiseCHOP', 'noise')
    nz.par.type.expr = "'random' if parent().par.Mode.eval() == 'whitenoise' else 'brownian'"
    if hasattr(nz.par, 'numint'):
        nz.par.numint.expr = "1 if parent().par.Mode.eval() == 'randomwalk' else 2"
    nz.par.seed.expr = 'parent().par.Seed'
    nz.par.period.expr = '1.0 / max(0.001, parent().par.Rate)'
    nz.par.periodunit = 'seconds'
    nz.par.amp = 1.0
    nz.par.offset = 0.0
    nz.par.channelname = 'value'

    # polarity: noise is ~ -1..1; clamp then map to the convention
    lim = c.create('limitCHOP', 'clamp')
    nz.outputConnectors[0].connect(lim.inputConnectors[0])
    for n in lim.par.type.menuNames:
        if 'clamp' in n.lower():
            lim.par.type = n
    lim.par.min, lim.par.max = -1.0, 1.0
    pol = c.create('mathCHOP', 'polarity')
    lim.outputConnectors[0].connect(pol.inputConnectors[0])
    pol.par.fromrange1, pol.par.fromrange2 = -1, 1
    pol.par.torange1.expr = "0 if parent().par.Polarity.eval() == 'unipolar' else -1"
    pol.par.torange2 = 1

    out1 = sg.out(c, pol)
    sg.help(c, 'sg_random - random source. Modes White Noise / Random Walk / Brownian. '
               'Deterministic Seed; Rate sets variation speed; value on the Polarity convention.\n')
    sg.arrange(c)
    return c, out1, nz


def verify(c, out1, nz):
    chans = [ch.name for ch in out1.chans()]
    # mode sweep: no errors, value finite per mode
    mode_checks = []
    for m in ('whitenoise', 'randomwalk', 'brownian'):
        c.par.Mode = m
        v = float(out1['value'].eval())
        mode_checks.append({'mode': m, 'val': round(v, 4), 'finite': v == v and abs(v) < 1e6})
    c.par.Mode = 'whitenoise'
    # determinism: same seed -> same noise value at the same time sample (read twice, no time change)
    c.par.Seed = 7
    a = float(nz['value'].eval())
    b = float(nz['value'].eval())
    return {
        'module': c.path,
        'out_channels': chans,
        'has_value': 'value' in chans,
        'mode_checks': mode_checks,
        'deterministic_same_cook': abs(a - b) < 1e-9,
        'params': [p.name for p in c.customPars],
        'errors': sg.errors(c),
    }


c, out1, nz = build()
result = verify(c, out1, nz)
