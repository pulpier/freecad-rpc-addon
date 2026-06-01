# freecad-rpc-addon

A FreeCAD addon that runs an **XML-RPC server inside the FreeCAD GUI process**,
so external Python clients can drive FreeCAD (create/edit/delete objects, save
documents, take screenshots, run FEM, execute arbitrary Python on the GUI
thread). Localhost-only, zero configuration, auto-starts when FreeCAD launches.

The recommended client is [`freecad-rpc`](https://github.com/pulpier/freecad-rpc).

## Background

Originally forked from [neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp)
as `pulpier/freecad-mcp`. The upstream project bundles two pieces — a FreeCAD
addon (XML-RPC server) and a Model Context Protocol wrapper for Claude Desktop.
**This fork keeps only the addon.** The MCP layer, workbench UI, settings file,
and remote-IP filtering are removed; install it and forget about it.

## What's in this repo

```
addon/FreeCADRPC/         the addon you symlink into FreeCAD's Mod directory
├── Init.py
├── InitGui.py            QTimer.singleShot autostart on FreeCAD's GUI thread
└── rpc_server/
    ├── rpc_server.py     the XML-RPC server + FreeCADRPC handler class
    ├── gui_dispatch.py   ferries work onto FreeCAD's GUI thread
    ├── object_factory.py, property_mapper.py, serialize.py,
    ├── view_manager.py, parts_library.py, fem_executor.py
examples/
└── cantilever_fem.py     end-to-end FEM smoke test (direct XML-RPC, no client lib)
```

## Install

```bash
git clone https://github.com/pulpier/freecad-rpc-addon.git
cd freecad-rpc-addon
git checkout add-save-close-document   # branch with save_document + close_document endpoints
```

Symlink the addon into FreeCAD's Mod directory:

| OS | Path |
|---|---|
| **macOS, FreeCAD 1.1** | `~/Library/Application Support/FreeCAD/v1-1/Mod/` |
| **macOS, FreeCAD 1.0** | `~/Library/Application Support/FreeCAD/Mod/` |
| **Linux** | `~/.local/share/FreeCAD/Mod/` |
| **Windows** | `%APPDATA%\FreeCAD\Mod\` |

```bash
# macOS FreeCAD 1.1:
ln -s "$PWD/addon/FreeCADRPC" ~/Library/Application\ Support/FreeCAD/v1-1/Mod/FreeCADRPC
```

Restart FreeCAD. You should see in the report view:

```
[freecad-rpc] RPC server started at 127.0.0.1:9875.
```

There is **no menu, no toolbar, no settings**. The server starts on launch and
stays up for the FreeCAD session.

## Verify

Using the [`freecad-rpc`](https://github.com/pulpier/freecad-rpc) Python client:

```python
from freecad_rpc import FreeCADClient
fc = FreeCADClient()
assert fc.ping()
print(fc.list_documents())
```

Or directly with `xmlrpc.client`:

```python
import xmlrpc.client
s = xmlrpc.client.ServerProxy("http://127.0.0.1:9875")
assert s.ping()
print(s.list_documents())
```

## RPC methods

| Category | Methods |
|---|---|
| Lifecycle | `ping()` |
| Documents | `create_document(name)`, `list_documents()`, `save_document(name, file_path=None)`, `close_document(name)`, `reload_document(name)` |
| Objects | `create_object(doc, obj_data)`, `edit_object(doc, name, obj_data)`, `delete_object(doc, name)`, `get_object(doc, name)`, `get_objects(doc)` |
| Parts library | `get_parts_list()`, `insert_part_from_library(rel_path)` |
| Screenshots | `get_active_screenshot(view, width, height, focus_object)` |
| Code execution | `execute_code(code)`, `execute_code_async(code)` |
| FEM | `run_fem_analysis(doc, analysis_name, timeout)` |

All methods that touch the document or GUI run on FreeCAD's main thread via the
`gui_dispatch` module, so concurrent calls serialise safely.

## Security

The server binds to `127.0.0.1` only. There is no authentication — anything that
can open a local socket on port 9875 can drive FreeCAD, including arbitrary
Python via `execute_code`. Don't enable remote access by editing this addon
without thinking carefully about that surface.

## Updating

```bash
cd ~/devel/freecad-rpc-addon && git pull

# Apply addon changes to running FreeCAD without restart:
python3 -c "from freecad_rpc import FreeCADClient, recipes; recipes.hot_reload_addon(FreeCADClient())"
```

Structural changes (renamed/deleted modules) need a FreeCAD restart;
`importlib.reload` can't handle those.

## License

MIT. See [LICENSE](./LICENSE).
