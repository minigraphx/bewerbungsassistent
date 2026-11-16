"""Whether the app runs from the MSIX package of the Microsoft Store (#344, G6), and the fixed path of its alias.

In the package the Store brings updates, the package manifest declares the link `bewerbungsbegleiter://`, and the
program sits in a folder under WindowsApps whose name carries the version. Whatever must keep finding the app after a
Store update, such as the browsers for the native messaging host, therefore points to the app alias instead, which
the package manifest declares (desktop/msix/AppxManifest.xml).
"""
import os
import pathlib
import sys
from collections.abc import Callable, Mapping

ALIAS = "bewerbungsbegleiter.exe"
# GetCurrentPackageFullName answers this outside a package; inside one, with no buffer, it asks for a larger one.
APPMODEL_ERROR_NO_PACKAGE = 15700
ERROR_INSUFFICIENT_BUFFER = 122
PACKAGED = (0, ERROR_INSUFFICIENT_BUFFER)


def _package_name_status() -> int:
    import ctypes
    length = ctypes.c_uint32(0)
    return ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)


def running_packaged(platform: str = sys.platform, status: Callable[[], int] = _package_name_status) -> bool:
    """True only when Windows names a package identity for this process; any doubt counts as the installer build."""
    if platform != "win32":
        return False
    try:
        return status() in PACKAGED
    except (OSError, AttributeError):
        return False


def alias_path(environ: Mapping[str, str] = os.environ) -> pathlib.PureWindowsPath:
    local = environ.get("LOCALAPPDATA") or str(pathlib.PureWindowsPath(environ.get("USERPROFILE", ""), "AppData", "Local"))
    return pathlib.PureWindowsPath(local, "Microsoft", "WindowsApps", ALIAS)
