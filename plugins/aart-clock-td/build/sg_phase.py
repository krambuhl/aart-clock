"""sg_phase.py - off-grid normalized looping phase.

Run via the bridge:
    g = dict(globals()); exec(open(<this>).read(), g); result = g['result']

Builds /project1/aart_clock/sg_phase. The off-grid specialist (per the fat-clock
seam): a free-running phase at an arbitrary Hz rate, decoupled from the transport
grid. sg_clock owns beat-synced phase; this owns everything off the grid.
Idempotent. Raw TD API (pre-sg-helper).

Input (in1): a pulse to align/reset the phase to (e.g. sg_clock's pulse_bar) - this is what
makes clock -> phase -> map a literal chain. Free-running when nothing is wired.
Outputs: phase, ramp (alias of phase), pulse_wrap (one-sample pulse at each wrap).
Params: Rate (Hz), Offset (0..1 phase offset), Synctoinput (reset phase on an input pulse).
"""

NS_PATH = '/project1/aart_clock'
MOD_PATH = NS_PATH + '/sg_phase'


def _set_menu(par, want):
    for n in par.menuNames:
        if want in n.lower():
            par.val = n
            return n
    return None


def _add_params(c):
    pg = c.appendCustomPage('Aartclock')
    pg.appendFloat('Rate', label='Rate (Hz)')
    c.par.Rate.default = 1.0
    c.par.Rate.val = 1.0
    c.par.Rate.normMin, c.par.Rate.normMax = 0.0, 10.0
    pg.appendFloat('Offset')
    c.par.Offset.default = 0.0
    c.par.Offset.val = 0.0
    c.par.Offset.normMin, c.par.Offset.normMax = 0.0, 1.0
    pg.appendToggle('Synctoinput', label='Sync To Input')
    c.par.Synctoinput.default = True
    c.par.Synctoinput.val = True


def build():
    ns = op(NS_PATH)
    ex = op(MOD_PATH)
    if ex:
        ex.destroy()
    c = ns.create('baseCOMP', 'sg_phase')
    c.comment = 'off-grid normalized phase (free Hz) - LFO ramp + wrap pulse'
    c.tags = ['aart-clock', 'timing']
    c.color = (0.5, 0.45, 0.3)
    _add_params(c)

    # reset input: a pulse on in1 re-zeros the phase, aligning it to an upstream clock.
    # this is the chain seam: wire e.g. sg_clock pulse_bar -> sg_phase in1.
    in1 = c.create('inCHOP', 'in1')
    reset_expr = "1 if (parent().par.Synctoinput and op('in1').numChans and op('in1')[0] > 0.5) else 0"

    # ramp source (0..1); name its channel `phase` directly
    ramp = c.create('lfoCHOP', 'ramp_lfo')
    ramp.par.wavetype = 'ramp'
    ramp.par.frequency.expr = 'parent().par.Rate'
    ramp.par.phase.expr = 'parent().par.Offset'
    ramp.par.channelname = 'phase'
    ramp.par.reset.expr = reset_expr

    # wrap pulse: an LFO 'pulse' type at the same freq/phase fires one sample per cycle
    pulse = c.create('lfoCHOP', 'wrap_lfo')
    pulse.par.wavetype = 'pulse'
    pulse.par.frequency.expr = 'parent().par.Rate'
    pulse.par.phase.expr = 'parent().par.Offset'
    pulse.par.channelname = 'pulse_wrap'
    pulse.par.reset.expr = reset_expr

    # `ramp` is an alias of `phase` (same value, contract completeness)
    n_ramp = c.create('renameCHOP', 'name_ramp')
    ramp.outputConnectors[0].connect(n_ramp.inputConnectors[0])
    n_ramp.par.renamefrom = '*'
    n_ramp.par.renameto = 'ramp'

    merge = c.create('mergeCHOP', 'internal')
    for src in (ramp, n_ramp, pulse):
        src.outputConnectors[0].connect(merge.inputConnectors[len(merge.inputs)])

    out1 = c.create('outCHOP', 'out1')
    merge.outputConnectors[0].connect(out1.inputConnectors[0])

    h = c.create('textDAT', 'help')
    h.text = 'sg_phase - off-grid phase. Outputs phase (0..1), ramp (alias), pulse_wrap. Rate in Hz.\n'

    return c, out1


def verify(c, out1):
    chans = sorted(ch.name for ch in out1.chans())
    phase_val = round(float(out1['phase'].eval()), 4) if 'phase' in chans else None
    errs = []
    for child in list(c.findChildren()) + [c]:
        ce = child.errors(recurse=False)
        if ce:
            errs += ['%s: %s' % (child.name, e) for e in ce.splitlines()]
    return {
        'module': c.path,
        'out_channels': chans,
        'has_contract': set(['phase', 'ramp', 'pulse_wrap']).issubset(set(chans)),
        'phase_val': phase_val,
        'phase_in_range': (phase_val is None) or (0.0 <= phase_val < 1.0001),
        'params': [p.name for p in c.customPars],
        'errors': errs,
    }


c, out1 = build()
result = verify(c, out1)
