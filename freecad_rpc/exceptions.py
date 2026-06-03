"""Exceptions raised by freecad_rpc."""


class FreeCADError(Exception):
    """Base exception for all freecad_rpc errors."""


class FreeCADRPCError(FreeCADError):
    """Raised when an RPC call returns ``success=False``.

    The original error message from the FreeCAD side is in ``args[0]``.
    The full server response dict is available as ``self.response``.
    """

    def __init__(self, message: str, response: dict | None = None):
        super().__init__(message)
        self.response = response or {}
