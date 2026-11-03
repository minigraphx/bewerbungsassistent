"""One root folder for Typst, also when the files lie on different drives.

Typst only reads files inside its root folder. Usually that is the common parent of the themes, the build
folder and the photo. On Windows they can lie on different drives (the app on C:, the data on D:), and there
is no common parent: then the themes and the photo are copied into the build folder, which becomes the root.
"""
import dataclasses
import os
import pathlib
import shutil
from collections.abc import Mapping, Sequence

STAGE = "typst-stamm"  # folder inside the build folder for the copies


@dataclasses.dataclass(frozen=True)
class TypstRoot:
    path: pathlib.Path
    moved: Mapping[pathlib.Path, pathlib.Path] = dataclasses.field(default_factory=dict)

    def locate(self, original: pathlib.Path) -> pathlib.Path:
        """Where Typst reads this file or a file inside a given folder."""
        original = original.resolve()
        for source, target in self.moved.items():
            if original == source or source in original.parents:
                return target / original.relative_to(source)
        return original

    def typst_path(self, original: pathlib.Path) -> str:
        """Path as Typst expects it, relative to the root."""
        return "/" + self.locate(original).relative_to(self.path).as_posix()


def _inside(path: pathlib.Path, folder: pathlib.Path) -> bool:
    return path == folder or folder in path.parents


def _stage(build: pathlib.Path, sources: Sequence[pathlib.Path]) -> TypstRoot:
    stage = build / STAGE
    moved = {}
    for index, source in enumerate(s for s in sources if not _inside(s, build)):
        target = stage / f"{index}-{source.name}"
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        moved[source] = target
    return TypstRoot(build, moved)


def typst_root(build: pathlib.Path, sources: Sequence[pathlib.Path]) -> TypstRoot:
    """A root for the build folder and the given folders and files (themes, photo)."""
    build = build.resolve()
    sources = [s.resolve() for s in sources]
    try:
        return TypstRoot(pathlib.Path(os.path.commonpath([build, *sources])))
    except ValueError:  # different drives: no common parent
        return _stage(build, sources)
