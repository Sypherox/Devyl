import os
import re
import gzip
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

IGNORED_PREFIXES = [
    "Player", "Dev", "Test", "User", "Guest", "Default",
    "Unknown", "Spieler", "Admin", "Mod", "Staff",
]
IGNORED_EXACT = {
    "Steve", "Alex", "Herobrine", "null", "none", "localhost",
    "server", "console", "system",
}
_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,16}$')
_PATTERN     = re.compile(r'Setting user:\s*(\S+)')


def _is_valid_username(name: str) -> bool:
    if not name:
        return False
    if not _USERNAME_RE.match(name):
        return False
    if name.lower() in {s.lower() for s in IGNORED_EXACT}:
        return False
    if any(name.lower().startswith(p.lower()) for p in IGNORED_PREFIXES):
        return False
    return True


def _get_mc_paths() -> list[str]:
    appdata  = os.environ.get("APPDATA", "")
    profile  = os.environ.get("USERPROFILE", "")
    localapp = os.environ.get("LOCALAPPDATA", "")

    candidates = [
        os.path.join(appdata,  r".minecraft\logs"),
        os.path.join(appdata,  r".minecraft\logs\blclient\minecraft"),
        os.path.join(appdata,  r".minecraft\logs\blclient"),
        os.path.join(appdata,  r"CheatBreaker\downloads\logs"),
        os.path.join(appdata,  r"CheatBreaker\logs"),
        os.path.join(profile,  r".lunarclient\logs"),
        os.path.join(profile,  r".lunarclient\logs\game"),
        os.path.join(appdata,  r".feather\logs"),
        os.path.join(appdata,  r"feather\logs"),
        os.path.join(appdata,  r"PrismLauncher\instances"),
        os.path.join(appdata,  r"MultiMC\instances"),
        os.path.join(appdata,  r"GDLauncher\instances"),
        os.path.join(appdata,  r"ATLauncher\instances"),
        os.path.join(appdata,  r"CurseForge\minecraft\Instances"),
        os.path.join(appdata,  r".pvplounge\logs"),
        os.path.join(appdata,  r"Badlion Client\logs"),
        os.path.join(appdata,  r"LabyMod\logs"),
        os.path.join(appdata,  r"labymod-neo\logs"),
    ]

    keywords = re.compile(
        r'minecraft|lunar|feather|badlion|pvp|labymod|forge|fabric|'
        r'cheatbreaker|blclient|tlauncher|pojav|sklauncher',
        re.IGNORECASE
    )
    for root in [appdata, localapp, profile]:
        if not root or not os.path.isdir(root):
            continue
        try:
            for entry in os.scandir(root):
                if not entry.is_dir(follow_symlinks=False):
                    continue
                if not keywords.search(entry.name):
                    continue
                candidates.append(entry.path)
                try:
                    for sub in os.scandir(entry.path):
                        if sub.is_dir() and sub.name.lower() in ("logs", "game"):
                            candidates.append(sub.path)
                except Exception:
                    pass
        except Exception:
            pass

    return list({p for p in candidates if p and os.path.isdir(p)})


def _collect_files(paths: list[str], max_bytes: int) -> list[str]:
    seen  = set()
    files = []
    for base in paths:
        try:
            for dirpath, _, filenames in os.walk(base):
                for fn in filenames:
                    if not (fn.endswith(".log") or fn.endswith(".gz")):
                        continue
                    full = os.path.join(dirpath, fn)
                    if full in seen:
                        continue
                    seen.add(full)
                    try:
                        if os.path.getsize(full) <= max_bytes:
                            files.append(full)
                    except OSError:
                        pass
        except Exception:
            pass
    return files


def _scan_file(path: str) -> list[str]:
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        return _PATTERN.findall(content)
    except Exception:
        return []


class LogAccountScanner:

    def run(self, max_file_size_mb: int = 50) -> dict:
        try:
            max_bytes = max_file_size_mb * 1024 * 1024
            paths     = _get_mc_paths()
            files     = _collect_files(paths, max_bytes)

            print(f"DEBUG LOG SCANNER: {len(paths)} paths, {len(files)} files")

            mention_count: Counter       = Counter()
            paths_by_name: dict[str, list] = {}
            lock = threading.Lock()

            def process(fp):
                names = _scan_file(fp)
                local = []
                for n in names:
                    if _is_valid_username(n):
                        local.append((n, fp))
                return local

            with ThreadPoolExecutor(max_workers=16) as exe:
                futures = {exe.submit(process, f): f for f in files}
                for fut in as_completed(futures):
                    try:
                        for name, fp in fut.result():
                            with lock:
                                mention_count[name] += 1
                                paths_by_name.setdefault(name, []).append(fp)
                    except Exception:
                        pass

            accounts = []
            for name, count in mention_count.most_common():
                accounts.append({
                    "name":          name,
                    "uuid":          None,
                    "uuid_dashed":   None,
                    "sources":       ["Log Files"],
                    "log_paths":     paths_by_name.get(name, []),
                    "mention_count": count,
                    "main":          False,
                    "maybe_main":    False,
                    "from_log":      True,
                })

            print(f"DEBUG LOG SCANNER: found {len(accounts)} accounts")
            return {
                "accounts":    accounts,
                "total_found": len(accounts),
                "error":       "",
            }

        except Exception as e:
            print(f"DEBUG LOG SCANNER ERROR: {e}")
            return {"accounts": [], "total_found": 0, "error": str(e)}
