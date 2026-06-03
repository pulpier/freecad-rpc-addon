# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-06-01

### Added
- `recipes.hot_reload_addon(client)` — restart the addon's RPC server
  in-place via `importlib.reload()` + stop/start, without restarting
  FreeCAD or losing open documents. Useful when iterating on addon-side
  changes (`rpc_server.py`). Documents a known one-shot GUI-dispatch race
  that may require retrying the first post-reload call.

### Fixed
- `recipes._extract_result_json` now handles the addon's `Output: <captured>`
  stdout wrapper, so recipes that pass JSON back via `print("RESULT_JSON:…")`
  parse reliably. Affected `describe_object` and `get_property`.

## [0.1.0] — 2026-06-01

### Added
- Initial release.
- **`FreeCADClient`** — XML-RPC client for the FreeCAD addon (covers
  documents, objects, screenshots, code execution, FEM solver).
- New endpoints exposed in the client (require the addon fork at
  `github.com/pulpier/freecad-rpc-addon` branch `add-save-close-document`):
  - `save_document(doc_name, file_path=None)` — in-place save or Save As.
  - `close_document(doc_name)` — close, discarding unsaved changes.
- Convenience: `save_screenshot(path, …)` — writes PNG directly to disk
  instead of returning base64.
- **`recipes`** module — audited `execute_code` snippets for operations the
  raw RPC API can't do (or does badly):
  - `set_part_group`, `add_to_part` — attach children to an `App::Part`
    (works around the FreeCAD 1.0.2 `edit_object` `Group` bug).
  - `set_active_container` — programmatic equivalent of the GUI's
    "double-click to make active" gesture.
  - `set_expression`, `clear_expression` — bind / unbind a property to a
    FreeCAD expression (e.g. `Vars.height`).
  - `describe_object`, `get_property` — safe introspection that bypasses
    the addon's `ShapeColor` `AttributeError` for non-shape objects.
- `FreeCADError` / `FreeCADRPCError` exception types.
- README with API tables, security model, known limitations.
- Three example scripts: `01_basic.py`, `02_part_group.py`, `03_expressions.py`.

[Unreleased]: https://github.com/pulpier/freecad-rpc/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/pulpier/freecad-rpc/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pulpier/freecad-rpc/releases/tag/v0.1.0
