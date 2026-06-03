"""freecad_rpc — minimal Python client for ``freecad-rpc-addon``.

Talks via XML-RPC to the addon's server, which runs inside the FreeCAD GUI
process. Exposes a granular Python API for document, object, screenshot, and
code-execution operations.

Quick start::

    from freecad_rpc import FreeCADClient

    fc = FreeCADClient()
    fc.ping()
    fc.create_document("scratch")
    fc.list_documents()
    fc.save_document("scratch", "/tmp/scratch.FCStd")
    fc.close_document("scratch")

High-level operations (audited ``execute_code`` snippets) live in
:mod:`freecad_rpc.recipes`::

    from freecad_rpc import recipes

    recipes.set_part_group(fc, "alles", "Bett_Klein",
                           ["Bett_Boxspring", "Bett_Matratze"])
    recipes.set_expression(fc, "alles", "Wall_N", "Height", "Vars.height")
"""

from . import recipes
from .client import FreeCADClient, FreeCADConnection
from .exceptions import FreeCADError, FreeCADRPCError

__all__ = [
    "FreeCADClient",
    "FreeCADConnection",  # deprecated alias for FreeCADClient
    "FreeCADError",
    "FreeCADRPCError",
    "recipes",
]

__version__ = "0.2.0"
