"""sg - thin build-helper library for aart-clock module build scripts.

Extracted from the shared patterns in sg_clock.py / sg_phase.py / sg_map.py
(rule of three). Build scripts import it and call these to follow the module
standard without re-deriving it. Pure TD API; no module-specific logic.

Usage from a build script run via the bridge:

    import sys
    sys.path.insert(0, '/Users/krambuhl/Sites/aart-clock/plugins/aart-clock-td/build')
    import sg
    c = sg.module('/project1/aart_clock', 'sg_foo', comment='...', color=(0.5,0.3,0.3))
    sg.pfloat(c, 'Bpm', 120, 20, 300, label='BPM')
    ...
    sg.out(c, sg.merge(c, 'internal', [a, b]))

`op` is resolved from TD's builtins at call time (available inside the bridge exec).
"""

import td  # TD's module API; imported modules don't get the injected `op` builtin

PAGE = 'Aartclock'


def _op(path):
    return td.op(path)


def module(ns_path, name, comment='', tags=('aart-clock',), color=(0.3, 0.3, 0.3)):
    """Create (idempotently) a module Base COMP under ns_path with the standard page."""
    ns = _op(ns_path)
    ex = _op(ns_path + '/' + name)
    if ex:
        ex.destroy()
    c = ns.create('baseCOMP', name)
    c.comment = comment
    c.tags = list(tags)
    c.color = color
    c.appendCustomPage(PAGE)
    return c


def _page(c):
    for p in c.customPages:
        if p.name == PAGE:
            return p
    return c.appendCustomPage(PAGE)


def pfloat(c, name, default=0.0, lo=None, hi=None, label=None):
    _page(c).appendFloat(name, label=label or name)
    p = getattr(c.par, name)
    p.default = default
    p.val = default
    if lo is not None:
        p.normMin = lo
    if hi is not None:
        p.normMax = hi
    return p


def pint(c, name, default=0, label=None):
    _page(c).appendInt(name, label=label or name)
    p = getattr(c.par, name)
    p.default = default
    p.val = default
    return p


def ptoggle(c, name, default=False, label=None):
    _page(c).appendToggle(name, label=label or name)
    p = getattr(c.par, name)
    p.default = default
    p.val = default
    return p


def ppulse(c, name, label=None):
    _page(c).appendPulse(name, label=label or name)
    return getattr(c.par, name)


def rename(c, name, src, frm, to):
    """Rename CHOP: positional space-separated frm -> to."""
    r = c.create('renameCHOP', name)
    src.outputConnectors[0].connect(r.inputConnectors[0])
    r.par.renamefrom = frm
    r.par.renameto = to
    return r


def merge(c, name, srcs):
    m = c.create('mergeCHOP', name)
    for s in srcs:
        s.outputConnectors[0].connect(m.inputConnectors[len(m.inputs)])
    return m


def out(c, src, name='out1'):
    o = c.create('outCHOP', name)
    src.outputConnectors[0].connect(o.inputConnectors[0])
    return o


def inchop(c, name='in1'):
    return c.create('inCHOP', name)


def help(c, text, name='help'):
    d = c.create('textDAT', name)
    d.text = text
    return d


def arrange(comp, dx=200, dy=140, x0=0, y0=0):
    """Tidy a COMP's children into a left-to-right flow by topological depth.

    Flow operators (CHOP/TOP/SOP/MAT) are placed in columns by their longest
    input-chain depth; rows stagger downward within a column. Non-flow extras
    (DATs like help/ext, side COMPs like local_time/demo) drop into a lane below.
    Reproducible: build scripts call this so rebuilds stay clean.
    """
    kids = list(comp.children)
    idset = set(k.id for k in kids)
    depth = {}
    visiting = set()

    def _depth(o):
        if o.id in depth:
            return depth[o.id]
        if o.id in visiting:  # cycle guard
            return 0
        visiting.add(o.id)
        ins = [i for i in o.inputs if i and i.id in idset]
        depth[o.id] = 0 if not ins else 1 + max(_depth(i) for i in ins)
        visiting.discard(o.id)
        return depth[o.id]

    flow = [k for k in kids if k.family in ('CHOP', 'TOP', 'SOP', 'MAT')]
    extras = [k for k in kids if k not in flow]

    cols = {}
    for k in flow:
        cols.setdefault(_depth(k), []).append(k)
    for col in sorted(cols):
        for row, n in enumerate(cols[col]):
            n.nodeX = x0 + col * dx
            n.nodeY = y0 - row * dy
    lane_y = y0 + dy * 2
    for i, n in enumerate(extras):
        n.nodeX = x0 + i * dx
        n.nodeY = lane_y
    return depth


def errors(c):
    """All node-error strings under c (and c itself). Empty list == clean."""
    out_errs = []
    for ch in list(c.findChildren()) + [c]:
        ce = ch.errors(recurse=False)
        if ce:
            out_errs += ['%s: %s' % (ch.name, e) for e in ce.splitlines()]
    return out_errs
