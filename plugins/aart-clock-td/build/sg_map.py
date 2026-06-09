"""sg_map.py - signal mapping / shaping utility.

Run via the bridge:
    g = dict(globals()); exec(open(<this>).read(), g); result = g['result']

Builds /project1/aart_clock/sg_map. Deterministic, so verified by exact assertion.
Idempotent. Raw TD API (pre-sg-helper).

Transforms (chain): remap -> clamp -> quantize.
  remap   : Inlow/Inhigh -> Outlow/Outhigh (covers scale, offset, AND polarity:
            unipolar<->bipolar is just a range change). Invert swaps the output range.
  clamp   : optional clamp to [Clamplow, Clamphigh].
  quantize: optional quantize to N steps across the output range.
Output channel: `value`.
"""

NS_PATH = '/project1/aart_clock'
MOD_PATH = NS_PATH + '/sg_map'


def _set_limit_type(lim, want):
    """Set a Limit CHOP type by fuzzy name match (menu names vary by build)."""
    names = list(lim.par.type.menuNames)
    for n in names:
        if want in n.lower():
            lim.par.type = n
            return n
    return None


def _add_params(c):
    pg = c.appendCustomPage('Aartclock')
    for name, dflt in [('Inlow', 0.0), ('Inhigh', 1.0), ('Outlow', 0.0), ('Outhigh', 1.0)]:
        pg.appendFloat(name)
        getattr(c.par, name).default = dflt
        getattr(c.par, name).val = dflt
    pg.appendToggle('Invert')
    pg.appendToggle('Clamp')
    for name, dflt in [('Clamplow', 0.0), ('Clamphigh', 1.0)]:
        pg.appendFloat(name)
        getattr(c.par, name).default = dflt
        getattr(c.par, name).val = dflt
    pg.appendToggle('Quantize')
    pg.appendInt('Steps')
    c.par.Steps.default = 4
    c.par.Steps.val = 4


def build():
    ns = op(NS_PATH)
    ex = op(MOD_PATH)
    if ex:
        ex.destroy()
    c = ns.create('baseCOMP', 'sg_map')
    c.comment = 'signal mapping - remap / clamp / quantize / polarity'
    c.tags = ['aart-clock', 'shaping']
    c.color = (0.3, 0.5, 0.35)
    _add_params(c)

    in1 = c.create('inCHOP', 'in1')

    # remap: scale/offset/invert/polarity via range conversion
    m = c.create('mathCHOP', 'remap')
    in1.outputConnectors[0].connect(m.inputConnectors[0])
    m.par.fromrange1.expr = 'parent().par.Inlow'
    m.par.fromrange2.expr = 'parent().par.Inhigh'
    # invert swaps the output endpoints
    m.par.torange1.expr = 'parent().par.Outhigh if parent().par.Invert else parent().par.Outlow'
    m.par.torange2.expr = 'parent().par.Outlow if parent().par.Invert else parent().par.Outhigh'

    # clamp: condition via bounds (bypass is a node flag, not exprable) - wide open when off
    clamp = c.create('limitCHOP', 'clamp')
    m.outputConnectors[0].connect(clamp.inputConnectors[0])
    _set_limit_type(clamp, 'clamp')
    clamp.par.min.expr = 'parent().par.Clamplow if parent().par.Clamp else -1e18'
    clamp.par.max.expr = 'parent().par.Clamphigh if parent().par.Clamp else 1e18'

    # quantize: step = output span / Steps when on; negligible step (~passthrough) when off
    quant = c.create('limitCHOP', 'quantize')
    clamp.outputConnectors[0].connect(quant.inputConnectors[0])
    _set_limit_type(quant, 'quant')
    if hasattr(quant.par, 'vstep'):
        quant.par.vstep.expr = (
            '((parent().par.Outhigh - parent().par.Outlow) / max(1, parent().par.Steps))'
            ' if parent().par.Quantize else 1e-9'
        )

    # output channel -> `value`
    rn = c.create('renameCHOP', 'name_value')
    quant.outputConnectors[0].connect(rn.inputConnectors[0])
    rn.par.renamefrom = '*'
    rn.par.renameto = 'value'
    out1 = c.create('outCHOP', 'out1')
    rn.outputConnectors[0].connect(out1.inputConnectors[0])

    h = c.create('textDAT', 'help')
    h.text = 'sg_map - remap (Inlow/Inhigh -> Outlow/Outhigh), Invert, Clamp, Quantize. Output channel: value.\n'

    return c, out1


def _reset_params(c):
    for n, v in [('Inlow', 0.0), ('Inhigh', 1.0), ('Outlow', 0.0), ('Outhigh', 1.0),
                 ('Invert', False), ('Clamp', False), ('Clamplow', 0.0), ('Clamphigh', 1.0),
                 ('Quantize', False), ('Steps', 4)]:
        getattr(c.par, n).val = v


def verify(c, out1):
    ns = c.parent()
    # drive a known input through the module
    tc = ns.op('_map_test') or ns.create('constantCHOP', '_map_test')
    tc.par.name0 = 'chan1'
    tc.outputConnectors[0].connect(c.inputConnectors[0])

    def read(inval, **pars):
        _reset_params(c)
        for k, v in pars.items():
            getattr(c.par, k).val = v
        tc.par.value0 = inval
        return round(float(out1['value'].eval()), 4)

    cases = [
        ('identity 0.5', read(0.5), 0.5),
        ('remap 0.5 -> 0..2 = 1.0', read(0.5, Outhigh=2.0), 1.0),
        ('offset 0.0 -> 0.5..1 = 0.5', read(0.0, Outlow=0.5, Outhigh=1.0), 0.5),
        ('invert 0.25 over 0..1 = 0.75', read(0.25, Invert=True), 0.75),
        ('polarity uni->bi: 0.5 -> -1..1 = 0.0', read(0.5, Outlow=-1.0, Outhigh=1.0), 0.0),
        ('clamp 2.0 to 0..1 = 1.0', read(2.0, Clamp=True), 1.0),
    ]
    _reset_params(c)
    # cleanup the test driver
    tc.destroy()

    checks = [{'name': n, 'got': got, 'want': want, 'pass': abs(got - want) < 1e-3} for (n, got, want) in cases]
    return {
        'module': c.path,
        'out_channels': [ch.name for ch in out1.chans()],
        'params': [p.name for p in c.customPars],
        'checks': checks,
        'all_pass': all(x['pass'] for x in checks),
    }


c, out1 = build()
result = verify(c, out1)
