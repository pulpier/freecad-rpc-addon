"""Auto-start the freecad-rpc XML-RPC server when FreeCAD's GUI is ready.

This add-on used to ship with a workbench (Start/Stop/Toggle commands and
IP-filter settings). Since we now operate exclusively as a localhost-only
RPC service for the `freecad-rpc` Python client, all of that UI is gone.
The server starts automatically and there's nothing to configure.
"""

import FreeCAD
from PySide import QtCore


def _start_rpc():
    try:
        from rpc_server import rpc_server
        msg = rpc_server.start_rpc_server()
        FreeCAD.Console.PrintMessage(f"[freecad-rpc] {msg}\n")
    except Exception as e:
        FreeCAD.Console.PrintWarning(f"[freecad-rpc] auto-start failed: {e}\n")


# Defer until the Qt event loop is up, so init_waker() can create its bridge.
QtCore.QTimer.singleShot(0, _start_rpc)
