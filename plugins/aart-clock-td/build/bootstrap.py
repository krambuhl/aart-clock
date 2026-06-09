"""bootstrap.py - construct the aart_clock namespace + module template via the MCP bridge.

Run through the TouchDesigner MCP bridge with:

    exec(open('/Users/krambuhl/Sites/aart-clock/plugins/aart-clock-td/build/bootstrap.py').read())

The bridge captures the module-level `result` variable (not stdout / not `return`;
see docs/SEED-RUNBOOK.md > bridge execution notes).

Idempotent: destroys and rebuilds /project1/aart_clock so the result is reproducible.
The namespace COMP is the shipped container that becomes plugins/aart-clock-td/aart_clock.tox.
"""

NS_PARENT = '/project1'
NS_NAME = 'aart_clock'
NS_PATH = NS_PARENT + '/' + NS_NAME


def build_namespace():
    parent = op(NS_PARENT)
    ex = op(NS_PATH)
    if ex:
        ex.destroy()
    ns = parent.create('baseCOMP', NS_NAME)
    ns.comment = 'aart-clock - modular signal toolkit (container)'
    ns.tags = ['aart-clock']
    ns.color = (0.15, 0.35, 0.55)
    return ns


def build_template(ns):
    """The module template: demonstrates the in/out/params/ext/docs/demo/internal standard.

    Modules don't clone this; the build scripts (and later the sg helper) follow the same
    shape. The template is the canonical reference + a smoke test that the standard is buildable.
    """
    t = ns.create('baseCOMP', 'sg_template')
    t.comment = 'module template (in / out / params / ext / docs / demo / internal)'
    t.tags = ['aart-clock', 'template']
    t.color = (0.3, 0.3, 0.3)

    # --- in / out: the I/O connector convention (In/Out CHOPs) ---
    in1 = t.create('inCHOP', 'in1')
    out1 = t.create('outCHOP', 'out1')

    # --- internal: the CHOP-graph implementation (here a passthrough placeholder) ---
    passthru = t.create('nullCHOP', 'internal')
    in1.outputConnectors[0].connect(passthru.inputConnectors[0])
    passthru.outputConnectors[0].connect(out1.inputConnectors[0])

    # --- ext: the extension scaffold (XxxExt class, wired + promoted + initialized) ---
    ext = t.create('textDAT', 'TemplateExt')
    ext.text = (
        'class TemplateExt:\n'
        '\t"""Base extension shape for aart-clock modules."""\n'
        '\tdef __init__(self, owner):\n'
        '\t\tself.owner = owner\n'
    )
    t.par.extension1 = 'op("./TemplateExt").module.TemplateExt(me)'
    t.par.promoteextension1 = True
    t.initializeExtensions()

    # --- docs: embedded help text ---
    helpd = t.create('textDAT', 'help')
    helpd.text = (
        'sg_template\n'
        '===========\n'
        'aart-clock module template. Each module follows this shape:\n'
        '  in/out  - In/Out CHOPs (signal I/O, channel-contract names)\n'
        '  params  - custom parameter page\n'
        '  ext     - <Name>Ext extension class\n'
        '  docs    - this help DAT\n'
        '  demo    - example patch (doubles as verification artifact)\n'
        '  internal- the CHOP-graph implementation\n'
        '\n'
        'NOTE: a "Pulse" signal is a one-sample event, distinct from TD\'s native\n'
        'Trigger CHOP (an ADSR envelope generator that sg_env is built on).\n'
    )

    # --- demo: example-patch placeholder ---
    demo = t.create('baseCOMP', 'demo')
    demo.comment = 'example patch / verification artifact'

    # --- params: the standard page marker (modules append their own params here) ---
    t.appendCustomPage('Aartclock')

    return t


def verify(ns, t):
    out1 = op(t.path + '/out1')
    return {
        'namespace': ns.path,
        'template': t.path,
        'children': sorted(c.name for c in t.children),
        'out1_wired_from': [c.name for c in out1.inputs],
        'extension_count': len(t.extensions),
        'custom_pages': [pg.name for pg in t.customPages],
        'help_len': len(op(t.path + '/help').text),
    }


def run():
    ns = build_namespace()
    t = build_template(ns)
    import sys as _sys
    _bp = '/Users/krambuhl/Sites/aart-clock/plugins/aart-clock-td/build'
    if _bp not in _sys.path:
        _sys.path.insert(0, _bp)
    import sg as _sg
    _sg.arrange(t)
    return verify(ns, t)


result = run()
