"""XML-RPC client for ``freecad-rpc-addon``.

The addon (https://github.com/pulpier/freecad-rpc-addon) must be installed in
FreeCAD's Mod directory. When FreeCAD starts, the addon runs an XML-RPC server
on ``127.0.0.1:9875`` inside the GUI process. This module is the Python client
for that server.

For the upstream workbench-based addon (``neka-nat/freecad-mcp``) the
connection still works, except the ``save_document`` / ``close_document``
endpoints — those exist only on this project's fork.
"""

from __future__ import annotations

import base64
import logging
import xmlrpc.client
from typing import Any

from .exceptions import FreeCADRPCError


logger = logging.getLogger(__name__)


class _TimeoutTransport(xmlrpc.client.Transport):
    """XML-RPC transport with a configurable socket timeout.

    The default ``Transport`` has no timeout, so a frozen FreeCAD GUI
    thread would hang the client indefinitely (observed: 4+ minute waits).
    """

    def __init__(self, timeout: float = 30, **kwargs):
        super().__init__(**kwargs)
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


class FreeCADClient:
    """Granular Python API for FreeCAD over XML-RPC.

    Talks to the ``freecad-rpc-addon``'s XML-RPC server (which runs on the
    FreeCAD GUI thread). All methods are synchronous and block until the GUI
    thread is free or the per-call timeout fires.

    Parameters
    ----------
    host : str, default "localhost"
        Hostname or IP of the FreeCAD machine. Only set this if you
        enabled remote connections in the addon's settings.
    port : int, default 9875
        Port the addon listens on.
    timeout : float, default 150
        Socket timeout in seconds for individual RPC calls.

    Raises
    ------
    ConnectionError
        If the addon isn't reachable (FreeCAD not running,
        addon not installed, wrong host/port).

    Examples
    --------
    >>> fc = FreeCADClient()
    >>> fc.ping()
    True
    >>> fc.create_document("scratch")
    {'success': True, 'document_name': 'scratch'}
    >>> fc.list_documents()
    ['scratch']
    """

    DEFAULT_PORT = 9875

    def __init__(
        self,
        host: str = "localhost",
        port: int = DEFAULT_PORT,
        timeout: float = 150,
    ):
        self.host = host
        self.port = port
        self.server = xmlrpc.client.ServerProxy(
            f"http://{host}:{port}",
            allow_none=True,
            transport=_TimeoutTransport(timeout=timeout),
        )

    # ---- lifecycle ----

    def disconnect(self) -> None:
        """Close cached HTTP connections (if any)."""
        transport = getattr(self.server, "_ServerProxy__transport", None)
        close = getattr(transport, "close", None)
        if callable(close):
            close()

    def ping(self) -> bool:
        """Check that the addon is reachable. Returns True on success."""
        return self.server.ping()

    # ---- documents ----

    def create_document(self, name: str) -> dict[str, Any]:
        """Create a new (empty, unsaved) document.

        Parameters
        ----------
        name : str
            Document name. FreeCAD appends a suffix if a document with
            this name already exists.

        Returns
        -------
        dict
            ``{"success": True, "document_name": <actual name>}`` on success.
        """
        return self.server.create_document(name)

    def list_documents(self) -> list[str]:
        """Return the names of all currently open documents."""
        return self.server.list_documents()

    def save_document(
        self, doc_name: str, file_path: str | None = None
    ) -> dict[str, Any]:
        """Save an open document to disk.

        Without ``file_path``, performs an in-place save to the document's
        existing ``FileName`` (equivalent to ⌘+S in the GUI). Fails if the
        document has never been saved.

        With ``file_path``, performs Save As: writes a new ``.FCStd`` file
        and updates ``doc.FileName``. Required for the first save of a
        scratch document.

        Parameters
        ----------
        doc_name : str
            Name of the open document (from ``list_documents()``).
        file_path : str, optional
            Absolute path for Save As. Recommended extension: ``.FCStd``.

        Returns
        -------
        dict
            ``{"success": True, "document_name": ..., "file_path": ...}``
            or ``{"success": False, "error": ...}``.
        """
        return self.server.save_document(doc_name, file_path)

    def close_document(self, doc_name: str) -> dict[str, Any]:
        """Close an open document. Unsaved changes are discarded —
        call :meth:`save_document` first if you need to persist them.
        """
        return self.server.close_document(doc_name)

    def reload_document(self, doc_name: str) -> dict[str, Any]:
        """Close and re-open a document to pick up external file changes.

        Use this when something outside the FreeCAD GUI process (e.g. a
        headless ``freecadcmd`` script) modified the on-disk ``.FCStd``
        — the open GUI copy is otherwise unaware.
        """
        return self.server.reload_document(doc_name)

    # ---- objects ----

    def create_object(
        self, doc_name: str, obj_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new object in a document.

        Parameters
        ----------
        doc_name : str
            Target document.
        obj_data : dict
            Object specification with keys:

            - ``Name`` (str): the object's internal name.
            - ``Type`` (str): FreeCAD type, e.g. ``"Part::Box"``,
              ``"Part::Cylinder"``, ``"App::Part"``, ``"Draft::Circle"``,
              ``"Fem::AnalysisPython"``.
            - ``Properties`` (dict, optional): property values, e.g.
              ``{"Length": 100, "Placement": {...}}``.
            - ``Analysis`` (str, optional): name of an existing
              ``Fem::AnalysisPython`` container to attach to.

        Returns
        -------
        dict
            ``{"success": True, "object_name": ...}`` on success.
        """
        return self.server.create_object(doc_name, obj_data)

    def edit_object(
        self, doc_name: str, obj_name: str, obj_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update properties of an existing object.

        Parameters
        ----------
        doc_name, obj_name : str
            Target document and object.
        obj_data : dict
            ``{"Properties": {<prop>: <value>, ...}}`` — values follow
            the same format as :meth:`create_object`.

        Notes
        -----
        Known limitation (FreeCAD 1.0.2): ``PropertyLinkList`` on
        ``App::Part`` (the ``Group`` property) cannot be set via this
        call — the assignment silently produces an empty list. Use the
        ``set_part_group`` recipe instead, or attach children via
        ``part.addObject(child)`` from an ``execute_code`` snippet.
        """
        return self.server.edit_object(doc_name, obj_name, obj_data)

    def delete_object(self, doc_name: str, obj_name: str) -> dict[str, Any]:
        """Delete an object from a document."""
        return self.server.delete_object(doc_name, obj_name)

    def get_object(self, doc_name: str, obj_name: str) -> dict[str, Any]:
        """Return all properties of an object.

        Notes
        -----
        Known limitation (FreeCAD 1.0.2): fails for objects whose
        ViewProvider lacks ``ShapeColor`` (e.g. ``App::Part``,
        ``App::DocumentObjectGroup``). The addon attempts to read
        ``ViewObject.ShapeColor`` unconditionally and raises
        ``AttributeError``.
        """
        return self.server.get_object(doc_name, obj_name)

    def get_objects(self, doc_name: str) -> list[dict[str, Any]]:
        """Return all objects in a document with their properties.

        Subject to the same ``ShapeColor`` limitation as :meth:`get_object`
        — a single non-shape object in the document poisons the whole call.
        """
        return self.server.get_objects(doc_name)

    # ---- parts library ----

    def get_parts_list(self) -> list[str]:
        """Return relative paths of all parts in the FreeCAD ``parts_library`` addon.

        Empty list if ``parts_library`` is not installed.
        """
        return self.server.get_parts_list()

    def insert_part_from_library(self, relative_path: str) -> dict[str, Any]:
        """Insert a part from the ``parts_library`` addon into the active document."""
        return self.server.insert_part_from_library(relative_path)

    # ---- screenshots ----

    def get_active_screenshot(
        self,
        view_name: str = "Isometric",
        width: int | None = None,
        height: int | None = None,
        focus_object: str | None = None,
        focus_objects: list | None = None,
    ) -> str | None:
        """Capture a screenshot of the active 3D view as base64-encoded PNG.

        Parameters
        ----------
        view_name : str
            One of ``"Isometric"``, ``"Front"``, ``"Top"``, ``"Right"``,
            ``"Back"``, ``"Left"``, ``"Bottom"``, ``"Dimetric"``, ``"Trimetric"``.
            Pass ``"Current"`` (or ``None``) to KEEP the camera exactly as it
            is — use this to capture a camera you positioned yourself via
            ``execute_code``.
        width, height : int, optional
            Viewport size in pixels. Defaults to the current viewport.
        focus_object : str, optional
            Single object name to fit-to-view (``ViewSelection``); otherwise
            fits all objects (unless ``view_name="Current"``).
        focus_objects : list[str], optional
            Frame the *combined* bounding box of several objects. Takes
            precedence over ``focus_object``. This is the reliable way to zoom
            to a room/detail rather than the whole model.

        Returns
        -------
        str or None
            Base64-encoded PNG bytes, or ``None`` if the active view is
            non-3D (e.g. TechDraw, Spreadsheet) or the call failed.
        """
        try:
            return self.server.get_active_screenshot(
                view_name, width, height, focus_object, focus_objects
            )
        except Exception as e:
            logger.error(f"Error getting screenshot: {e}")
            return None

    def save_screenshot(
        self,
        path: str,
        view_name: str = "Isometric",
        width: int | None = None,
        height: int | None = None,
        focus_object: str | None = None,
        focus_objects: list | None = None,
    ) -> bool:
        """Capture a screenshot and write it as PNG to ``path``.

        Returns ``True`` on success, ``False`` if the view doesn't support
        screenshots. See :meth:`get_active_screenshot` for ``view_name``
        (incl. ``"Current"``), ``focus_object`` and ``focus_objects``.
        """
        b64 = self.get_active_screenshot(
            view_name, width, height, focus_object, focus_objects
        )
        if not b64:
            return False
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return True

    # ---- code execution ----

    def execute_code(self, code: str) -> dict[str, Any]:
        """Execute arbitrary Python code on the FreeCAD GUI thread.

        ⚠ **Powerful and unsafe.** Use only for trusted code. The recipes
        in :mod:`freecad_rpc.recipes` wrap specific common operations
        with fixed code templates; prefer those for production code paths.

        The code runs synchronously on FreeCAD's main GUI thread, so
        document mutations, ``recompute()`` and ``save()`` are safe and
        correctly ordered. Don't use this for heavy OCCT operations
        (fuse/cut/loft) that would block the GUI; use
        :meth:`execute_code_async` for those.

        Returns
        -------
        dict
            ``{"success": bool, "message": str, "output": str}``.
            ``output`` contains anything written to stdout.
        """
        return self.server.execute_code(code)

    def execute_code_async(self, code: str) -> dict[str, Any]:
        """Execute Python code in a background thread (returns immediately).

        ⚠ The code **must not** touch ``FreeCADGui``, the active view,
        selection, document objects, or call ``doc.recompute()`` / ``save()``.
        Background-safe operations only: heavy OCCT shape calculations
        on already-fetched shapes, CPU-bound math, etc.

        For document mutations use :meth:`execute_code` instead.
        """
        return self.server.execute_code_async(code)

    # ---- FEM ----

    def run_fem_analysis(
        self, doc_name: str, analysis_name: str, timeout: int = 600
    ) -> dict[str, Any]:
        """Run the CalculiX solver on an existing ``Fem::FemAnalysis`` container.

        Prerequisites in the document: a Part-derived solid, a
        ``Fem::AnalysisPython`` container, a ``Fem::MaterialCommon``
        bound to the geometry, a ``Fem::FemMeshGmsh``, and at least one
        ``Fem::ConstraintFixed`` and one ``Fem::ConstraintForce``.

        Blocks until the solver finishes or ``timeout`` (seconds) expires.

        Returns
        -------
        dict
            On success: ``max_von_mises_MPa``, ``max_displacement_mm``,
            ``min_displacement_mm``, ``node_count``, ``working_directory``.
            On failure: ``error`` describes the prerequisite or solver issue.
        """
        return self.server.run_fem_analysis(doc_name, analysis_name, timeout)


# Backwards-compatible alias matching the original neka-nat/freecad-mcp API.
FreeCADConnection = FreeCADClient


def _check_success(response: dict[str, Any], operation: str) -> dict[str, Any]:
    """Raise :class:`FreeCADRPCError` if response indicates failure, else return it."""
    if not response.get("success"):
        raise FreeCADRPCError(
            f"{operation} failed: {response.get('error', '<no error message>')}",
            response=response,
        )
    return response
