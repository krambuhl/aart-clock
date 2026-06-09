"""sg_env.py - envelope generator (wraps TD's Trigger CHOP).

Run via the bridge:
    g = dict(globals()); exec(open(<this>).read(), g); result = g['result']

Builds /project1/aart_clock/sg_env. The Trigger CHOP IS TD's native ADSR generator; this wraps
it behind the aart-clock contract. Feed a gate/pulse into in1 (e.g. sg_clock pulse_beat or
sg_divide gate); out1 carries `env` (0..1). Idempotent. Uses the sg build-helper.

Params: Attack, Decay, Release (seconds), Sustain (level 0..1), Mode (AR/AD/ADSR/Loop).
Mode shapes the envelope by expression:
  AR   - no decay, sustain held at peak, release on gate-off
  AD   - decay to zero, no sustain hold, completes per trigger (ignores gate length)
  ADSR - full envelope
  Loop - completes + re-triggers every (A+D+R) -> repeating envelope
NOTE: "Trigger CHOP" is TD's envelope op; an aart-clock "Pulse" is the one-sample event that
fires it. Different things sharing a near-name - see help.
"""

import sys

BUILD = '/Users/krambuhl/Sites/aart-clock/plugins/aart-clock-td/build'
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)
import sg  # noqa: E402

NS = '/project1/aart_clock'
MOD = NS + '/sg_env'


def build():
    c = sg.module(NS, 'sg_env', comment='envelope generator (wraps Trigger CHOP)',
                  tags=('aart-clock', 'shaping'), color=(0.45, 0.35, 0.55))
    sg.pfloat(c, 'Attack', 0.05, 0.0, 2.0, label='Attack (s)')
    sg.pfloat(c, 'Decay', 0.1, 0.0, 2.0, label='Decay (s)')
    sg.pfloat(c, 'Sustain', 0.7, 0.0, 1.0, label='Sustain')
    sg.pfloat(c, 'Release', 0.3, 0.0, 2.0, label='Release (s)')
    page = next(p for p in c.customPages if p.name == 'Aartclock')
    page.appendMenu('Mode')
    c.par.Mode.menuNames = ['ar', 'ad', 'adsr', 'loop']
    c.par.Mode.menuLabels = ['AR', 'AD', 'ADSR', 'Loop']
    c.par.Mode.default = 'adsr'
    c.par.Mode.val = 'adsr'

    in1 = sg.inchop(c, 'in1')

    tr = c.create('triggerCHOP', 'env_gen')
    in1.outputConnectors[0].connect(tr.inputConnectors[0])
    # threshold is a toggle; threshup/threshdown are the actual levels (default 0 -> a 0->1 gate
    # never crosses). Trigger above 0.5, release below 0.5.
    tr.par.threshold = True
    if hasattr(tr.par, 'threshup'):
        tr.par.threshup = 0.5
    if hasattr(tr.par, 'threshdown'):
        tr.par.threshdown = 0.5
    M = "parent().par.Mode.eval()"
    tr.par.attack.expr = 'parent().par.Attack'
    tr.par.decay.expr = "0 if %s == 'ar' else parent().par.Decay" % M
    tr.par.sustain.expr = "1 if %s == 'ar' else (0 if %s == 'ad' else parent().par.Sustain)" % (M, M)
    tr.par.release.expr = 'parent().par.Release'
    tr.par.complete.expr = "1 if %s in ('ad', 'loop') else 0" % M
    if hasattr(tr.par, 'retrigger'):
        tr.par.retrigger.expr = (
            "(parent().par.Attack + parent().par.Decay + parent().par.Release) "
            "if %s == 'loop' else 0" % M
        )

    rn = sg.rename(c, 'name_env', tr, '*', 'env')
    out1 = sg.out(c, rn)
    sg.help(c, 'sg_env - ADSR envelope (wraps the Trigger CHOP). Feed a gate/pulse into in1; '
               'out1 = env (0..1). Modes AR/AD/ADSR/Loop. NOTE: TD\'s "Trigger CHOP" is the '
               'envelope op; an aart-clock Pulse is the event that fires it.\n')
    sg.arrange(c)
    return c, out1, tr


def verify(c, out1, tr):
    # structural: with a driver connected, out1 must carry `env`. Dynamic envelope response
    # is verified separately (it needs cooks between gate changes, not a single-cook read).
    ns = c.parent()
    drv = ns.op('_env_test') or ns.create('constantCHOP', '_env_test')
    drv.par.name0 = 'g'
    drv.par.value0 = 1.0
    drv.outputConnectors[0].connect(c.inputConnectors[0])
    chans = [ch.name for ch in out1.chans()]
    res = {
        'module': c.path,
        'out_channels': chans,
        'has_env': 'env' in chans,
        'trigger_input_wired': len(tr.inputs) > 0,
        'params': [p.name for p in c.customPars],
        'mode_default': str(c.par.Mode.eval()),
        'errors': sg.errors(c),
    }
    drv.destroy()
    return res


c, out1, tr = build()
result = verify(c, out1, tr)
