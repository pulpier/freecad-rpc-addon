"""High-level operations that wrap :meth:`FreeCADClient.execute_code` with fixed,
audited Python templates.

Use these instead of raw ``execute_code`` when you want a constrained surface
area — each recipe accepts only well-typed arguments and embeds them safely
into a known-good code template. The library still exposes ``execute_code``
for unrestricted use; an Allowlist-style configuration (e.g. Claude Code's
``permissions.allow``) can grant access to ``recipes.*`` without granting
arbitrary code execution.

All recipes are synchronous and execute on the FreeCAD GUI thread.
"""

from __future__ import annotations

import json
from typing import Any

from .client import FreeCADClient
from .exceptions import FreeCADRPCError


def _q(value: str) -> str:
    """JSON-encode a Python value for safe embedding into a code template.

    Strings become JSON-quoted strings; this prevents injection of quotes,
    newlines, or backslashes in user-supplied identifiers.
    """
    return json.dumps(value)


def _run(client: FreeCADClient, code: str, operation: str) -> dict[str, Any]:
    res = client.execute_code(code)
    if not res.get("success"):
        raise FreeCADRPCError(
            f"{operation} failed: {res.get('message', res.get('error', '<no message>'))}",
            response=res,
        )
    return res


# ---------------------------------------------------------------------------
# App::Part — group children, set active container
# ---------------------------------------------------------------------------

def set_part_group(
    client: FreeCADClient,
    doc_name: str,
    part_name: str,
    child_names: list[str],
    recompute: bool = True,
) -> dict[str, Any]:
    """Attach a list of objects as children of an ``App::Part`` container.

    Replaces the existing children with ``child_names``. After this call,
    ``Part.Placement`` correctly transforms all children (which is the
    whole point of using ``App::Part`` instead of ``DocumentObjectGroup``).

    This is the recommended workaround for the FreeCAD 1.0.2 limitation
    where :meth:`FreeCADClient.edit_object` cannot set the ``Group``
    ``PropertyLinkList`` of an ``App::Part``.

    Parameters
    ----------
    client : FreeCADClient
    doc_name : str
        Document containing the Part and its (already created) children.
    part_name : str
        Internal name of the ``App::Part``.
    child_names : list of str
        Internal names of the children to attach, in order.
    recompute : bool, default True
        Whether to call ``doc.recompute()`` after the assignment.

    Returns
    -------
    dict
        The raw ``execute_code`` response.

    Raises
    ------
    FreeCADRPCError
        If the document, part, or any child is not found.

    Examples
    --------
    >>> set_part_group(fc, "alles", "Bett_Klein",
    ...                ["Bett_Boxspring", "Bett_Matratze", "Bett_Topper"])
    """
    code = (
        "import FreeCAD\n"
        f"doc = FreeCAD.getDocument({_q(doc_name)})\n"
        f"part = doc.getObject({_q(part_name)})\n"
        "assert part is not None, 'part not found'\n"
        f"children = {json.dumps(child_names)}\n"
        "objs = []\n"
        "for n in children:\n"
        "    o = doc.getObject(n)\n"
        "    assert o is not None, f'child not found: {n}'\n"
        "    objs.append(o)\n"
        "part.Group = objs\n"
        f"{'doc.recompute()' if recompute else ''}\n"
        "print('RESULT: Group set, len=' + str(len(part.Group)))\n"
    )
    return _run(client, code, f"set_part_group({part_name!r})")


def add_to_part(
    client: FreeCADClient,
    doc_name: str,
    part_name: str,
    child_name: str,
    recompute: bool = True,
) -> dict[str, Any]:
    """Add a single object as a child of an ``App::Part`` (preserves existing children)."""
    code = (
        "import FreeCAD\n"
        f"doc = FreeCAD.getDocument({_q(doc_name)})\n"
        f"part = doc.getObject({_q(part_name)})\n"
        f"child = doc.getObject({_q(child_name)})\n"
        "assert part is not None, 'part not found'\n"
        "assert child is not None, 'child not found'\n"
        "part.addObject(child)\n"
        f"{'doc.recompute()' if recompute else ''}\n"
        "print('RESULT: child added, len=' + str(len(part.Group)))\n"
    )
    return _run(client, code, f"add_to_part({part_name!r}, {child_name!r})")


def set_active_container(
    client: FreeCADClient,
    doc_name: str,
    part_name: str | None,
) -> dict[str, Any]:
    """Set (or clear) the active container in the GUI tree.

    When a container is active, objects newly created via
    :meth:`FreeCADClient.create_object` are automatically attached to
    it (FreeCAD's standard behavior). Pass ``part_name=None`` to clear
    the active container.
    """
    if part_name is None:
        code = (
            "import FreeCADGui\n"
            "FreeCADGui.ActiveDocument.ActiveView.setActiveObject('part', None)\n"
            "print('RESULT: active container cleared')\n"
        )
    else:
        code = (
            "import FreeCAD\n"
            "import FreeCADGui\n"
            f"doc = FreeCAD.getDocument({_q(doc_name)})\n"
            f"part = doc.getObject({_q(part_name)})\n"
            "assert part is not None, 'part not found'\n"
            "FreeCADGui.ActiveDocument.ActiveView.setActiveObject('part', part)\n"
            f"print('RESULT: active container = ' + {_q(part_name)})\n"
        )
    return _run(client, code, f"set_active_container({part_name!r})")


# ---------------------------------------------------------------------------
# Expressions — bind a property to a VarSet / spreadsheet cell / arbitrary expr
# ---------------------------------------------------------------------------

def set_expression(
    client: FreeCADClient,
    doc_name: str,
    obj_name: str,
    prop_path: str,
    expression: str,
    recompute: bool = True,
) -> dict[str, Any]:
    """Bind an object property to an expression.

    Equivalent to ``obj.setExpression(prop_path, expression)``. Used to
    couple geometry to a central VarSet / Spreadsheet for parametric
    models, e.g.::

        set_expression(fc, "alles", "Wall_North", "Height", "Vars.height")
        set_expression(fc, "alles", "Win_S_1", "Placement.Base.x",
                       "Vars.win_x - Vars.win_w / 2")

    To clear a binding pass ``expression=None`` (must call
    :func:`clear_expression`).

    Parameters
    ----------
    prop_path : str
        Property path, possibly nested, e.g. ``"Length"``,
        ``"Placement.Base.x"``, ``"Placement.Rotation.Angle"``.
    expression : str
        FreeCAD expression syntax. Must NOT be ``None`` — use
        :func:`clear_expression` for that.
    """
    code = (
        "import FreeCAD\n"
        f"doc = FreeCAD.getDocument({_q(doc_name)})\n"
        f"obj = doc.getObject({_q(obj_name)})\n"
        "assert obj is not None, 'object not found'\n"
        f"obj.setExpression({_q(prop_path)}, {_q(expression)})\n"
        f"{'doc.recompute()' if recompute else ''}\n"
        "print('RESULT: expression set')\n"
    )
    return _run(
        client, code, f"set_expression({obj_name!r}, {prop_path!r})"
    )


def clear_expression(
    client: FreeCADClient,
    doc_name: str,
    obj_name: str,
    prop_path: str,
    recompute: bool = True,
) -> dict[str, Any]:
    """Remove an expression binding from an object property (keeps the current value)."""
    code = (
        "import FreeCAD\n"
        f"doc = FreeCAD.getDocument({_q(doc_name)})\n"
        f"obj = doc.getObject({_q(obj_name)})\n"
        "assert obj is not None, 'object not found'\n"
        f"obj.setExpression({_q(prop_path)}, None)\n"
        f"{'doc.recompute()' if recompute else ''}\n"
        "print('RESULT: expression cleared')\n"
    )
    return _run(
        client, code, f"clear_expression({obj_name!r}, {prop_path!r})"
    )


# ---------------------------------------------------------------------------
# Addon lifecycle — hot-reload the RPC server without restarting FreeCAD
# ---------------------------------------------------------------------------

def hot_reload_addon(
    client: FreeCADClient, settle_ms: int = 500
) -> dict[str, Any]:
    """Restart the addon's RPC server in-place to pick up addon code changes —
    no FreeCAD restart, no open documents lost.

    Useful during addon development: after editing
    ``addon/FreeCADRPC/rpc_server/rpc_server.py`` on disk (or following a
    symlink to a working copy), call this once to re-register the new
    ``FreeCADRPC`` class. Documents stay open; clients reconnect on the
    next call.

    The reload runs deferred via ``QTimer.singleShot`` so this method
    returns cleanly before the server thread that's processing the call
    gets torn down. Wait ~1 second before the next RPC call.

    Known quirk
    -----------
    The **first** RPC call after the reload may time out with
    ``GUI dispatch timed out after Ns``. The retry succeeds. This is a
    one-shot race between the new server's GUI-dispatch queue and the
    Qt event loop's heartbeat timer; subsequent calls are fine.

    Parameters
    ----------
    client : FreeCADClient
    settle_ms : int, default 500
        Milliseconds to wait inside FreeCAD before stop+reload+start.

    Returns
    -------
    dict
        The ``execute_code`` response confirming the reload was scheduled.

    Examples
    --------
    Typical development cycle::

        # 1. edit rpc_server.py in your fork
        # 2. apply the change to the running FreeCAD without restart:
        from freecad_rpc import FreeCADClient, recipes
        fc = FreeCADClient()
        recipes.hot_reload_addon(fc)
        # 3. test the new endpoint (first call may need a retry)
    """
    code = (
        "import importlib\n"
        "import FreeCAD\n"
        "from PySide import QtCore\n"
        "import rpc_server.rpc_server as rs\n"
        "\n"
        "def do_reload():\n"
        "    try:\n"
        "        FreeCAD.Console.PrintMessage('[hot_reload] stopping RPC server...\\n')\n"
        "        rs.stop_rpc_server()\n"
        "        FreeCAD.Console.PrintMessage('[hot_reload] reloading module...\\n')\n"
        "        importlib.reload(rs)\n"
        "        FreeCAD.Console.PrintMessage('[hot_reload] starting RPC server...\\n')\n"
        "        msg = rs.start_rpc_server()\n"
        "        FreeCAD.Console.PrintMessage('[hot_reload] done: ' + str(msg) + '\\n')\n"
        "    except Exception as e:\n"
        "        import traceback\n"
        "        FreeCAD.Console.PrintError('[hot_reload] failed: ' + str(e) + '\\n' + traceback.format_exc())\n"
        "\n"
        f"QtCore.QTimer.singleShot({int(settle_ms)}, do_reload)\n"
        "print('RESULT: hot_reload scheduled')\n"
    )
    return _run(client, code, "hot_reload_addon")


# ---------------------------------------------------------------------------
# Generic introspection — avoids the ShapeColor AttributeError in get_object
# ---------------------------------------------------------------------------

def describe_object(
    client: FreeCADClient,
    doc_name: str,
    obj_name: str,
) -> dict[str, Any]:
    """Return type, label, and property names of an object — safe for any FreeCAD type.

    Workaround for the FreeCAD 1.0.2 limitation where
    :meth:`FreeCADClient.get_object` raises ``AttributeError`` on objects
    whose ViewProvider lacks ``ShapeColor`` (``App::Part``,
    ``App::DocumentObjectGroup``, etc.).

    Returns a dict with ``Name``, ``Label``, ``TypeId``, and
    ``PropertiesList`` (list of property name strings).
    """
    code = (
        "import FreeCAD\n"
        "import json\n"
        f"doc = FreeCAD.getDocument({_q(doc_name)})\n"
        f"obj = doc.getObject({_q(obj_name)})\n"
        "assert obj is not None, 'object not found'\n"
        "info = {\n"
        "    'Name': obj.Name,\n"
        "    'Label': obj.Label,\n"
        "    'TypeId': obj.TypeId,\n"
        "    'PropertiesList': list(obj.PropertiesList),\n"
        "}\n"
        "print('RESULT_JSON:' + json.dumps(info))\n"
    )
    res = _run(client, code, f"describe_object({obj_name!r})")
    return _extract_result_json(res)


def get_property(
    client: FreeCADClient,
    doc_name: str,
    obj_name: str,
    prop_name: str,
) -> Any:
    """Read a single property value via ``execute_code``. Repr-coerced to string.

    Useful for properties that don't round-trip cleanly through the
    XML-RPC layer (FreeCAD ``Vector``, ``Placement``, ``Quantity``).
    """
    code = (
        "import FreeCAD\n"
        "import json\n"
        f"doc = FreeCAD.getDocument({_q(doc_name)})\n"
        f"obj = doc.getObject({_q(obj_name)})\n"
        "assert obj is not None, 'object not found'\n"
        f"value = getattr(obj, {_q(prop_name)})\n"
        "print('RESULT_JSON:' + json.dumps({'repr': repr(value), 'str': str(value)}))\n"
    )
    res = _run(client, code, f"get_property({obj_name!r}.{prop_name})")
    return _extract_result_json(res)


_RESULT_MARKER = "RESULT_JSON:"


def _extract_result_json(response: dict[str, Any]) -> Any:
    """Pull the ``RESULT_JSON:`` payload out of an execute_code response.

    The addon wraps captured stdout as ``"Output: <captured>"`` and embeds
    that in the ``message`` field, so the marker may sit mid-line. We scan
    every line for the marker and parse from there to the end of line.
    """
    output = response.get("output", "") or response.get("message", "")
    for line in output.splitlines():
        idx = line.find(_RESULT_MARKER)
        if idx >= 0:
            return json.loads(line[idx + len(_RESULT_MARKER):])
    raise FreeCADRPCError(
        "recipe returned no RESULT_JSON line", response=response
    )
