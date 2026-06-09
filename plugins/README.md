# plugins

TouchDesigner components (`.tox` packages) this project depends on or ships.

- **`touchdesigner-mcp-td/`** — vendored, third-party. The [touchdesigner-mcp](https://github.com/8beeeaaat/touchdesigner-mcp) bridge (`mcp_webserver_base.tox` + `modules/`) that lets an agent drive a running TouchDesigner instance over HTTP. Do not move files within this directory — the `.tox` resolves `modules/` by relative path. Used only at build time.
- **`aart-clock-td/`** — first-party. The aart-clock toolkit itself: a single distributable `aart_clock.tox` containing the `sg_*` signal modules, produced from the Python build scripts in its `build/` directory.
