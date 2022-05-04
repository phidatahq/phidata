from pathlib import Path


def rmdir_recursive(dir: Path) -> bool:
    """Deletes a dir recursively, including all files and dirs in that directory"""

    if not dir.exists():
        return True

    for item in dir.iterdir():
        if item.is_dir():
            rmdir_recursive(item)
        else:
            item.unlink()
    dir.rmdir()
    return True if not dir.exists() else False


def delete_from_fs(path_to_del: Path) -> bool:
    if not path_to_del.exists():
        return True
    if path_to_del.is_dir():
        return rmdir_recursive(path_to_del)
    else:
        path_to_del.unlink()
    return True if not path_to_del.exists() else False
