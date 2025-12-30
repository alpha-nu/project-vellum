from controller.path_protocol import PathLike
from domain.model.file import File


def file_from_path(path: PathLike) -> File:
    """Construct a domain `File` from a Path-like object.

    This function expects a Path-like object that provides `.name` and
    `.stat().st_size` (for example a `pathlib.Path` or a test mock that
    implements the `PathLike` protocol defined in `controller.path_protocol`).
    """
    p = path
    size = p.stat().st_size
    return File(name=p.name, size_bytes=size)
