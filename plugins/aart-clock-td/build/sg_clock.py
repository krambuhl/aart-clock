"""sg_clock.py - master transport (Time COMP + Beat CHOP).

Run via the bridge:
    g = dict(globals()); exec(open(<this>).read(), g); result = g['result']

Builds /project1/aart_clock/sg_clock, the sole beat-synced phase source.
Idempotent. Raw TD API (pre-sg-helper). See docs/SEED-RUNBOOK.md for the run pattern.

Outputs (canonical channel contract):
  beat / bar / phrase                  - counters
  phase_beat / phase_bar / phase_phrase - 0..1 ramps
  pulse_beat / pulse_bar / pulse_phrase - one-sample pulses
Params: Bpm, Play, Reset, Barbeats, Phrasebars (uppercase-first, no underscores).
"""

NS_PATH = '/project1/aart_clock'
MOD_PATH = NS_PATH + '/sg_clock'


def _add_params(c):
    pg = c.appendCustomPage('Aartclock')
    pg.appendFloat('Bpm', label='BPM')
    c.par.Bpm.default = 120
    c.par.Bpm.val = 120
    c.par.Bpm.normMin, c.par.Bpm.normMax = 20, 300
    pg.appendToggle('Play')
    c.par.Play.default = True
    c.par.Play.val = True
    pg.appendPulse('Reset')
    pg.appendInt('Barbeats', label='Beats Per Bar')
    c.par.Barbeats.default = 4
    c.par.Barbeats.val = 4
    pg.appendInt('Phrasebars', label='Bars Per Phrase')
    c.par.Phrasebars.default = 4
    c.par.Phrasebars.val = 4


def _beat_chop(c, name, period_expr):
    b = c.create('beatCHOP', name)
    b.par.op = 'local_time'                 # reference the module's local Time COMP
    b.par.period.expr = period_expr
    # emit exactly ramp + pulse + count; suppress the rest
    for on in ('ramp', 'pulse', 'count'):
        setattr(b.par, on, True)
    for off in ('sine', 'countramp', 'bar', 'beat'):
        if hasattr(b.par, off):
            setattr(b.par, off, False)
    return b


def _rename(c, name, src, frm, to):
    r = c.create('renameCHOP', name)
    src.outputConnectors[0].connect(r.inputConnectors[0])
    r.par.renamefrom = frm
    r.par.renameto = to
    return r


def build():
    ns = op(NS_PATH)
    ex = op(MOD_PATH)
    if ex:
        ex.destroy()
    c = ns.create('baseCOMP', 'sg_clock')
    c.comment = 'master transport - Time COMP + Beat CHOP'
    c.tags = ['aart-clock', 'timing']
    c.color = (0.55, 0.3, 0.3)

    _add_params(c)

    # internal Time COMP (Component Time) driven by the module params.
    # Run independently so the clock survives a global-timeline pause (RESEARCH s1).
    t = c.create('timeCOMP', 'local_time')
    if hasattr(t.par, 'independent'):
        t.par.independent = True
    if hasattr(t.par, 'tempo'):
        t.par.tempo.expr = 'parent().par.Bpm'
    if hasattr(t.par, 'play'):
        t.par.play.expr = 'parent().par.Play'

    # three period-scaled Beat CHOPs riding local_time
    beat = _beat_chop(c, 'beat', '1')
    bar = _beat_chop(c, 'bar', 'parent().par.Barbeats')
    phrase = _beat_chop(c, 'phrase', 'parent().par.Barbeats * parent().par.Phrasebars')

    # rename each to the canonical contract before merging (avoids name collisions)
    rb = _rename(c, 'name_beat', beat, 'ramp pulse count', 'phase_beat pulse_beat beat')
    ra = _rename(c, 'name_bar', bar, 'ramp pulse count', 'phase_bar pulse_bar bar')
    rp = _rename(c, 'name_phrase', phrase, 'ramp pulse count', 'phase_phrase pulse_phrase phrase')

    merge = c.create('mergeCHOP', 'internal')
    for src in (rb, ra, rp):
        src.outputConnectors[0].connect(merge.inputConnectors[len(merge.inputs)])

    out1 = c.create('outCHOP', 'out1')
    merge.outputConnectors[0].connect(out1.inputConnectors[0])

    # Reset handler: pulse the Beat CHOPs' reset on the module Reset pulse
    rexec = c.create('parameterexecuteDAT', 'reset_exec')
    rexec.par.op = '..'
    if hasattr(rexec.par, 'pulse'):
        rexec.par.pulse = True
    if hasattr(rexec.par, 'value'):
        rexec.par.value = False
    rexec.text = (
        'def onPulse(par):\n'
        '\tif par.name == "Reset":\n'
        '\t\tfor n in ("beat", "bar", "phrase"):\n'
        '\t\t\tb = par.owner.op(n)\n'
        '\t\t\tif b and hasattr(b.par, "resetpulse"):\n'
        '\t\t\t\tb.par.resetpulse.pulse()\n'
        '\treturn\n'
    )

    # docs
    h = c.create('textDAT', 'help')
    h.text = 'sg_clock - master transport.\nOutputs beat/bar/phrase counters, phase_* ramps (0..1), pulse_* one-sample pulses.\n'

    return c, out1


def verify(c, out1):
    chans = [ch.name for ch in out1.chans()]
    phase_chans = [n for n in chans if n.startswith('phase_')]
    phase_vals = {n: round(float(out1[n].eval()), 4) for n in phase_chans}
    # collect node errors across the module (avoid TD type globals; filter by family string)
    errs = []
    for child in list(c.findChildren()) + [c]:
        ce = child.errors(recurse=False)
        if ce:
            for e in ce.splitlines():
                errs.append('%s: %s' % (child.name, e))
    return {
        'module': c.path,
        'out_channels': sorted(chans),
        'channel_count': len(chans),
        'phase_in_range': all(0.0 <= v < 1.0001 for v in phase_vals.values()),
        'phase_vals': phase_vals,
        'bpm': float(c.par.Bpm.eval()),
        'params': [p.name for p in c.customPars],
        'errors': errs,
    }


c, out1 = build()
result = verify(c, out1)
