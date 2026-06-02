"""Active-view orientation, sizing, and screenshot capture."""

from typing import Any

import FreeCAD
import FreeCADGui

from .gui_dispatch import _flush_gui_events


_VIEW_DISPATCH = {
    "Isometric": "viewIsometric",
    "Front": "viewFront",
    "Top": "viewTop",
    "Right": "viewRight",
    "Back": "viewBack",
    "Left": "viewLeft",
    "Bottom": "viewBottom",
    "Dimetric": "viewDimetric",
    "Trimetric": "viewTrimetric",
}


def _get_view_size(view: Any) -> tuple[int, int]:
    try:
        size = view.getSize()
        if isinstance(size, (list, tuple)) and len(size) >= 2:
            return max(1, int(size[0])), max(1, int(size[1]))
        return max(1, int(size.width())), max(1, int(size.height()))
    except Exception:
        return 1024, 768


def _resolve_screenshot_size(
    view: Any,
    width: int | None,
    height: int | None,
) -> tuple[int, int]:
    view_width, view_height = _get_view_size(view)
    resolved_width = view_width if width is None else max(1, int(width))
    resolved_height = view_height if height is None else max(1, int(height))
    return resolved_width, resolved_height


_STD_COMMAND_DISPATCH = {
    "Isometric": "Std_ViewIsometric",
    "Front": "Std_ViewFront",
    "Top": "Std_ViewTop",
    "Right": "Std_ViewRight",
    "Back": "Std_ViewRear",
    "Left": "Std_ViewLeft",
    "Bottom": "Std_ViewBottom",
    "Dimetric": "Std_ViewDimetric",
    "Trimetric": "Std_ViewTrimetric",
}


def apply_view_orientation(view: Any, view_name: str) -> None:
    method_name = _VIEW_DISPATCH.get(view_name)
    if method_name is None:
        raise ValueError(f"Invalid view name: {view_name}")
    if hasattr(view, method_name):
        getattr(view, method_name)()
    else:
        # Fallback for views that lack the direct Python method
        # (e.g. some FreeCAD versions / view types)
        cmd = _STD_COMMAND_DISPATCH.get(view_name)
        if cmd:
            FreeCADGui.runCommand(cmd)
        else:
            FreeCAD.Console.PrintWarning(
                f"apply_view_orientation: no method or command for '{view_name}'\n"
            )


def save_active_screenshot(
    save_path: str,
    view_name: str = "Isometric",
    width: int | None = None,
    height: int | None = None,
    focus_object: str | None = None,
    focus_objects: list | None = None,
):
    """Save a PNG of the active view to ``save_path``.

    Returns ``True`` on success, or an error string on failure (preserves the
    legacy GUI-handler return contract).

    Camera control
    --------------
    ``view_name``
        A named orientation (``"Isometric"``, ``"Top"``, ``"Front"``, …) resets
        the camera to look along that axis. Pass ``"Current"`` (or ``None``) to
        KEEP the camera exactly as it is — use this to capture a camera you set
        up yourself via ``execute_code`` (position / pointAt / orthographic).
    ``focus_object`` / ``focus_objects``
        Frame the view tightly to a single object, or to the *combined*
        bounding box of several objects, via ``ViewSelection``. This is the
        reliable way to zoom to a room/detail — the fit happens inside this
        same GUI task, right before the image is saved, so it is never undone
        by a later ``fitAll``.

    Fit precedence: explicit focus targets → else a named ``view_name`` fits
    all objects → else (``"Current"`` with no focus) the camera is captured
    as-is, no fit.
    """
    try:
        view = FreeCADGui.ActiveDocument.ActiveView
        if not hasattr(view, "saveImage"):
            return "Current view does not support screenshots"

        keep_camera = view_name in (None, "", "Current")
        if not keep_camera:
            apply_view_orientation(view, view_name)

        # Collect focus targets (focus_objects takes precedence over the
        # legacy single focus_object).
        names = []
        if focus_objects:
            names = [n for n in focus_objects if n]
        elif focus_object:
            names = [focus_object]

        focused_selection = False
        if names:
            doc = FreeCAD.ActiveDocument
            objs = [doc.getObject(n) for n in names] if doc else []
            objs = [o for o in objs if o is not None]
            if objs:
                FreeCADGui.Selection.clearSelection()
                for o in objs:
                    FreeCADGui.Selection.addSelection(o)
                FreeCADGui.SendMsgToActiveView("ViewSelection")
                focused_selection = True
                _flush_gui_events()
                FreeCADGui.Selection.clearSelection()
            elif not keep_camera:
                view.fitAll()
        elif not keep_camera:
            view.fitAll()

        _flush_gui_events()
        resolved_width, resolved_height = _resolve_screenshot_size(view, width, height)
        view.saveImage(save_path, resolved_width, resolved_height, "Current")

        if focused_selection:
            FreeCADGui.Selection.clearSelection()
            _flush_gui_events(delay_ms=0)
        return True
    except Exception as e:
        return str(e)
