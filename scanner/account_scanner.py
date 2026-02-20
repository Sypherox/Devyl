import os
import json
import re
import struct
import urllib.request


class AccountScanner:
    def __init__(self):
        self.appdata = os.environ.get("APPDATA", "")
        self.userprofile = os.environ.get("USERPROFILE", "")

    def run(self):
        all_uuids = {}
        main_uuid = None

        cb_path = os.path.join(self.appdata, ".minecraft", "cheatbreaker_accounts.json")
        active_local_id = None
        try:
            with open(cb_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            active_local_id = data.get("activeAccountLocalId")
            for local_id, acc in data.get("accounts", {}).items():
                profile = acc.get("minecraftProfile", {})
                uuid = self._norm(profile.get("id", ""))
                name = profile.get("name", "")
                if uuid:
                    self._add(all_uuids, uuid, name, "CheatBreaker")
        except Exception:
            pass

        ms_path = os.path.join(self.appdata, ".minecraft", "launcher_accounts_microsoft_store.json")
        try:
            with open(ms_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            accounts = data.get("accounts", {})
            active_id = data.get("activeAccountLocalId") or data.get("mojangClientToken")
            for key, acc in accounts.items():
                profile = acc.get("minecraftProfile", {})
                uuid = self._norm(profile.get("id", ""))
                name = profile.get("name", "")
                if uuid:
                    self._add(all_uuids, uuid, name, "Launcher (MS Store)")
            if accounts:
                if active_id and active_id in accounts:
                    candidate = accounts[active_id].get("minecraftProfile", {})
                else:
                    candidate = next(iter(accounts.values())).get("minecraftProfile", {})
                main_uuid = self._norm(candidate.get("id", ""))
        except Exception:
            pass

        laby_neo_path = os.path.join(self.appdata, ".minecraft", "labymod-neo", "accounts.json")
        try:
            with open(laby_neo_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, acc in data.items():
                uuid = self._norm(key)
                name = acc.get("username", "") or acc.get("name", "")
                if not name:
                    name = acc.get("uuid", "")
                if uuid and len(uuid) == 32:
                    self._add(all_uuids, uuid, name, "LabyMod Neo")
        except Exception:
            pass

        badlion_path = os.path.join(self.appdata, "Badlion Client", "accounts.dat")
        try:
            uuids_found = self._extract_uuids_from_binary(badlion_path)
            for uuid in uuids_found:
                self._add(all_uuids, uuid, "", "Badlion")
        except Exception:
            pass

        laby_tokens_path = os.path.join(self.appdata, "LabyMod", "launcher-tokens.json")
        try:
            with open(laby_tokens_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in data.keys():
                uuid = self._norm(key)
                if uuid and len(uuid) == 32:
                    self._add(all_uuids, uuid, "", "LabyMod Launcher")
        except Exception:
            pass

        norisk_path = os.path.join(self.appdata, "norisk", "NoRiskClientV3", "accounts.json")
        try:
            with open(norisk_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            accs = data if isinstance(data, list) else data.get("accounts", [])
            for acc in accs:
                uuid = self._norm(acc.get("id", ""))
                name = acc.get("name", "") or acc.get("username", "")
                if uuid:
                    self._add(all_uuids, uuid, name, "NoRisk Client")
        except Exception:
            pass

        prism_path = os.path.join(self.appdata, "PrismLauncher", "accounts.json")
        try:
            with open(prism_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            accs = data.get("accounts", [])
            for acc in accs:
                profile = acc.get("profile", {}) or acc
                uuid = self._norm(profile.get("id", "") or acc.get("id", ""))
                name = profile.get("name", "") or acc.get("name", "")
                if uuid:
                    self._add(all_uuids, uuid, name, "Prism Launcher")
        except Exception:
            pass

        for lunar_path in [
            os.path.join(self.userprofile, ".lunarclient", "settings", "game", "accounts.json"),
            os.path.join(self.userprofile, ".lunarclient", "settings", "game-backup", "accounts.json"),
        ]:
            source = "Lunar Client" if "game-backup" not in lunar_path else "Lunar Client (backup)"
            try:
                with open(lunar_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                accs = data.get("accounts", data) if isinstance(data, dict) else data
                if isinstance(accs, dict):
                    accs = list(accs.values())
                for acc in accs:
                    profile = acc.get("minecraftProfile", {})
                    uuid = self._norm(profile.get("id", ""))
                    name = profile.get("name", "")
                    if uuid:
                        self._add(all_uuids, uuid, name, source)
            except Exception:
                pass

        feather_path = os.path.join(self.appdata, ".feather", "accounts.json")
        try:
            with open(feather_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            accs = data if isinstance(data, list) else data.get("accounts", [])
            for acc in accs:
                uuid = self._norm(acc.get("minecraftUuid", ""))
                name = acc.get("name", "") or acc.get("username", "")
                if uuid:
                    self._add(all_uuids, uuid, name, "Feather Client")
        except Exception:
            pass

        for uuid, info in all_uuids.items():
            if not info["name"]:
                info["name"] = self._fetch_name(uuid) or uuid

        if main_uuid and main_uuid in all_uuids:
            all_uuids[main_uuid]["main"] = True

        result = []
        for uuid, info in all_uuids.items():
            result.append({
                "uuid":    uuid,
                "uuid_dashed": self._to_dashed(uuid),
                "name":    info["name"],
                "sources": info["sources"],
                "main":    info.get("main", False),
            })

        result.sort(key=lambda x: (not x["main"], x["name"].lower()))

        main_name = next((a["name"] for a in result if a["main"]), None)
        return {"accounts": result, "main_name": main_name}

    def _norm(self, uuid_str: str) -> str:
        """Entfernt Bindestriche, lowercase"""
        return uuid_str.replace("-", "").lower().strip() if uuid_str else ""

    def _to_dashed(self, uuid: str) -> str:
        """xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx → xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"""
        u = uuid.replace("-", "")
        if len(u) != 32:
            return uuid
        return f"{u[0:8]}-{u[8:12]}-{u[12:16]}-{u[16:20]}-{u[20:32]}"

    def _add(self, store: dict, uuid: str, name: str, source: str):
        """Fügt UUID zur Liste hinzu, verhindert Duplikate"""
        if uuid not in store:
            store[uuid] = {"name": name, "sources": [source], "main": False}
        else:
            if name and not store[uuid]["name"]:
                store[uuid]["name"] = name
            if source not in store[uuid]["sources"]:
                store[uuid]["sources"].append(source)

    def _fetch_name(self, uuid: str) -> str:
        """Holt Accountnamen von Mojang API"""
        try:
            url = f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
            req = urllib.request.Request(url, headers={"User-Agent": "DevylScanner/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return data.get("name", "")
        except Exception:
            return ""

    def _extract_uuids_from_binary(self, path: str) -> list:
        """Extrahiert UUID-ähnliche Strings aus einer Binärdatei (Badlion .dat)"""
        uuids = []
        try:
            with open(path, "rb") as f:
                content = f.read()
            text = content.decode("latin-1")
            for m in re.finditer(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', text, re.IGNORECASE):
                uuids.append(self._norm(m.group()))
            for m in re.finditer(r'\b[0-9a-f]{32}\b', text, re.IGNORECASE):
                uuids.append(m.group().lower())
        except Exception:
            pass
        return list(set(uuids))
