import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Union, Generator


PathType = Union[str, Path]


def to_path(path: PathType) -> Path:
    if isinstance(path, Path):
        return path
    else:
        return Path(path)


def write_json_file(data: Any, path: PathType) -> None:
    path = to_path(path)
    f = NamedTemporaryFile(mode="w+", prefix=path.name, dir=str(path.parent))
    with f as tmp_file:
        json.dump(data, tmp_file, indent=4, sort_keys=True)
        shutil.move(tmp_file.name, path)
        # NamedTemporaryFile tries to delete the file and fails otherwise
        open(tmp_file.name, "a").close()


@contextmanager
def chdir(dest: PathType) -> Generator[None, None, None]:
    previous = os.getcwd()
    os.chdir(dest)
    try:
        yield
    finally:
        os.chdir(previous)
