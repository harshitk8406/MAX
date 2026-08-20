"""
MAX 2.0 — Deep File Manager Skill
Find, open, create, delete, move files and folders by voice.
"""
import os
import glob
import shutil
import subprocess
import datetime
from pathlib import Path
from skills.router import skill
from core.logger import log

# Common search roots
_SEARCH_ROOTS = [
    os.path.expanduser("~\\Desktop"),
    os.path.expanduser("~\\Documents"),
    os.path.expanduser("~\\Downloads"),
    os.path.expanduser("~\\Pictures"),
    os.path.expanduser("~\\Music"),
    os.path.expanduser("~\\Videos"),
    "D:\\",
    "C:\\Users",
]


def _find_file(name: str, roots=None) -> list[str]:
    """Search for files matching name across common directories."""
    results = []
    search_in = roots or _SEARCH_ROOTS
    name_lower = name.lower()
    for root in search_in:
        if not os.path.exists(root):
            continue
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                # Skip hidden/system dirs
                dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in
                                ('$Recycle.Bin', 'System Volume Information', '__pycache__', 'node_modules')]
                for fname in filenames:
                    if name_lower in fname.lower():
                        results.append(os.path.join(dirpath, fname))
                if len(results) >= 10:
                    return results
        except PermissionError:
            continue
    return results


@skill("find_file")
def find_file(args: dict, spoken: str) -> str:
    name = args.get("name", "") or args.get("query", "")
    if not name:
        from core.voice import take_command
        name = take_command(prompt="What file should I look for?")
    if not name:
        return "I didn't catch a file name."
    log.info(f"Searching for file: {name}")
    results = _find_file(name)
    if not results:
        return spoken or f"I couldn't find any file matching '{name}'. It might be in a non-standard location."
    if len(results) == 1:
        return spoken or f"Found it: {results[0]}"
    names = [os.path.basename(r) for r in results[:3]]
    return spoken or f"I found {len(results)} files matching '{name}'. The first few are: {', '.join(names)}."


@skill("open_file")
def open_file(args: dict, spoken: str) -> str:
    path = args.get("path", "") or args.get("name", "")
    if not path:
        from core.voice import take_command
        path = take_command(prompt="What file should I open?")
    if not path:
        return "I didn't catch a file name."

    # If it's not an absolute path, try to find it
    if not os.path.isabs(path) or not os.path.exists(path):
        results = _find_file(path)
        if results:
            path = results[0]
        else:
            return f"I couldn't find a file called '{path}'."

    try:
        os.startfile(path)
        return spoken or f"Opening {os.path.basename(path)}!"
    except Exception as e:
        log.error(f"Open file error: {e}")
        return f"Couldn't open that file: {e}"


@skill("create_folder")
def create_folder(args: dict, spoken: str) -> str:
    name = args.get("name", "") or args.get("folder", "")
    location = args.get("location", os.path.expanduser("~\\Desktop"))
    if not name:
        from core.voice import take_command
        name = take_command(prompt="What should I name the new folder?")
    if not name:
        return "I need a folder name."
    full_path = os.path.join(location, name)
    try:
        os.makedirs(full_path, exist_ok=True)
        return spoken or f"Created folder '{name}' on your Desktop."
    except Exception as e:
        log.error(f"Create folder error: {e}")
        return f"Couldn't create that folder: {e}"


@skill("delete_file")
def delete_file(args: dict, spoken: str) -> str:
    path = args.get("path", "") or args.get("name", "")
    if not path:
        from core.voice import take_command
        path = take_command(prompt="What file should I delete?")
    if not path:
        return "I need a file name."

    if not os.path.isabs(path) or not os.path.exists(path):
        results = _find_file(path)
        if results:
            path = results[0]
        else:
            return f"I couldn't find '{path}'."

    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return spoken or f"Deleted '{os.path.basename(path)}'."
    except Exception as e:
        log.error(f"Delete error: {e}")
        return f"I couldn't delete that: {e}"


@skill("list_files")
def list_files(args: dict, spoken: str) -> str:
    location = args.get("location", "") or args.get("path", "")
    if not location:
        location = os.path.expanduser("~\\Desktop")
    if not os.path.isdir(location):
        # Try to resolve common names
        named = {
            "desktop": os.path.expanduser("~\\Desktop"),
            "documents": os.path.expanduser("~\\Documents"),
            "downloads": os.path.expanduser("~\\Downloads"),
        }
        location = named.get(location.lower(), os.path.expanduser("~\\Desktop"))

    try:
        entries = os.listdir(location)[:12]
        if not entries:
            return f"The folder is empty."
        return spoken or f"Here are the files: {', '.join(entries[:8])}. There are {len(entries)} items total."
    except Exception as e:
        return f"Couldn't list that folder: {e}"


@skill("clear_temp")
def clear_temp(args: dict, spoken: str) -> str:
    """Clear Windows temp files."""
    import tempfile
    temp = tempfile.gettempdir()
    removed = 0
    errors = 0
    try:
        for item in os.listdir(temp):
            item_path = os.path.join(temp, item)
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    removed += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    removed += 1
            except Exception:
                errors += 1
    except Exception as e:
        return f"Couldn't access temp folder: {e}"
    return spoken or f"Cleaned up {removed} temp files. {f'{errors} were in use and skipped.' if errors else ''}"


@skill("disk_usage")
def disk_usage(args: dict, spoken: str) -> str:
    """Report disk space usage."""
    try:
        import psutil
        drives = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                pct = usage.percent
                free_gb = round(usage.free / (1024**3), 1)
                total_gb = round(usage.total / (1024**3), 1)
                drives.append(f"{part.device}: {free_gb} GB free of {total_gb} GB ({pct}% used)")
            except Exception:
                continue
        if drives:
            return spoken or "Disk usage — " + ". ".join(drives[:3])
        return "Couldn't read disk info."
    except Exception as e:
        return f"Disk check failed: {e}"
