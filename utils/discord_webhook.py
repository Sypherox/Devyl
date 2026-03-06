import requests
import os
from datetime import datetime


class DiscordWebhook:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_scan_result(self, scan_results, scan_id, html_report_path=None):
        account_data  = scan_results.get("accounts", {})
        mc_name       = account_data.get("main_name") or "Unknown"
        mc_accounts   = account_data.get("accounts", [])
        main_acc      = next((a for a in mc_accounts if a.get("main")), None)
        mc_uuid       = main_acc.get("uuid_dashed") or main_acc.get("uuid") if main_acc else None

        bypass        = scan_results.get("bypass_attempts", {})
        system_info   = scan_results.get("system_info", {})
        mouse_drivers = scan_results.get("mouse_drivers", [])
        banable       = scan_results.get("banable_programs", [])
        unsigned      = scan_results.get("unsigned", {})

        suspicious_fields = []

        for d in mouse_drivers:
            if d.get("suspicious"):
                suspicious_fields.append({
                    "name":   f"🖱️ Suspicious Driver: {d['driver']}",
                    "value":  f"```Path: {d['path']}\nFile: {d['file']}\nModified: {d['last_modified']}```",
                    "inline": False
                })

        for p in banable:
            if p.get("suspicious"):
                suspicious_fields.append({
                    "name":   f"⚠️ Banable Program: {p['name']}",
                    "value":  f"```Last Run: {p.get('last_run') or 'Unknown'}```",
                    "inline": False
                })

        dps_findings = scan_results.get("dps_findings", [])
        info_dps = [e for e in dps_findings if e["status"] == "info"]
        if info_dps:
            names = ", ".join(e["name"] for e in info_dps[:8])
            if len(info_dps) > 8:
                names += f" (+{len(info_dps)-8} more)"
            suspicious_fields.append({
                "name":   f"🧠 DPS Memory Strings ({len(info_dps)} found)",
                "value":  f"```{names}```",
                "inline": False
            })

        for key, label in [
            ("usn",                  "🗑️ USN Journal Cleared"),
            ("eventlogs",            "📋 Event Logs Cleared"),
            ("security_log_cleared", "🔒 Security Log Cleared"),
        ]:
            info = bypass.get(key, {})
            if info.get("level") == "Suspicious":
                suspicious_fields.append({
                    "name":   label,
                    "value":  f"```Time: {info.get('time') or 'Unknown'}```",
                    "inline": False
                })

        for key, label in [
            ("hidden_prefetch",    "👻 Hidden Prefetch Files"),
            ("readonly_prefetch",  "🔒 Read-Only Prefetch Files"),
            ("duplicate_prefetch", "📄 Duplicate Prefetch Files"),
        ]:
            info = bypass.get(key, {})
            if info.get("level") == "Suspicious":
                items = ", ".join(info.get("items", [])[:5])
                suspicious_fields.append({
                    "name":   label,
                    "value":  f"```{items}```",
                    "inline": False
                })

        for cf in unsigned.get("cheat_files", []):
            suspicious_fields.append({
                "name":  "🚨 Manthe Client Binary",
                "value": f"```File: {cf['name']}\nPath: {cf['path']}\nSize: {cf['size_mb']} MB\nModified: {cf['last_mod']}```",
                "inline": False
            })

        u_count = len(unsigned.get("unsigned_files", []))
        if u_count > 0:
            suspicious_fields.append({
                "name":   "🔓 Unsigned Executables in System32/SysWOW64/Temp",
                "value":  f"```{u_count} unsigned file(s) found```",
                "inline": False
            })

        renamed = bypass.get("renamed_exes", {})
        if renamed.get("level") == "Suspicious":
            items_text = "\n".join(
                f"{i.get('Path')} ({i.get('Extension')})"
                for i in renamed.get("items", [])[:3]
            )
            suspicious_fields.append({
                "name":   "🔄 Renamed Executables",
                "value":  f"```{items_text}```",
                "inline": False
            })

        rb = bypass.get("recycle_bin", {})
        if rb.get("level") == "Suspicious":
            suspicious_fields.append({
                "name":   "🗑️ Recycle Bin Activity",
                "value":  f"```Last Modified: {rb.get('last_modified') or 'Unknown'}\nLast Item: {rb.get('last_item') or 'Empty'}```",
                "inline": False
            })

        for svc in system_info.get("services", []):
            if svc.get("level") == "Suspicious":
                suspicious_fields.append({
                    "name":   f"⚙️ Service Stopped: {svc['name']}",
                    "value":  f"```{svc.get('reason', 'Unknown')}```",
                    "inline": False
                })

        for key, label in [
            ("cmd_logging",    "💻 CMD Logging Disabled"),
            ("ps_logging",     "💻 PS Logging Disabled"),
            ("prefetch",       "📁 Prefetch Disabled"),
            ("uav_disabled",   "👁️ UserAssist Disabled"),
            ("no_recent_docs", "📂 Recent Docs Disabled"),
        ]:
            if system_info.get(key) == "Suspicious":
                suspicious_fields.append({
                    "name":   f"🚨 {label}",
                    "value":  "```Suspicious registry value detected```",
                    "inline": False
                })

        if suspicious_fields:
            color  = 0xFF0000
            status = "⚠️ SUSPICIOUS"
        else:
            color  = 0x00FF88
            status = "✓ CLEAN"

        scan_duration = scan_results.get("scan_duration", 0)
        duration_str  = f"{scan_duration:.1f}s" if scan_duration < 60 else f"{int(scan_duration//60)}m {scan_duration%60:.0f}s"

        base_fields = [
            {"name": "🆔 Scan ID",   "value": f"`{scan_id}`",                              "inline": True},
            {"name": "📊 Result",     "value": status,                                       "inline": True},
            {"name": "⏱️ Duration",   "value": duration_str,                                 "inline": True},
            {"name": "🕐 Time",       "value": datetime.now().strftime('%d.%m.%Y %H:%M:%S'), "inline": True},
            {"name": "🚨 Findings",   "value": f"{len(suspicious_fields)} suspicious",       "inline": True},
        ]

        thumbnail_url = f"https://visage.surgeplay.com/bust/{mc_uuid}" if mc_uuid else None

        embed = {
            "title":       "🔎 Devyl Scan Result",
            "description": f"**Minecraft Account:** `{mc_name}`",
            "color":       color,
            "fields":      base_fields + (suspicious_fields if suspicious_fields else [
                {"name": "✅ No Suspicious Findings", "value": "All checks passed clean.", "inline": False}
            ]),
            "footer":    {"text": "Devyl DFIR Tool | sypherox.dev"},
            "timestamp": datetime.now().isoformat(),
        }

        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}

        payload = {
            "username": "Devyl",
            "embeds":   [embed]
        }

        try:
            response = requests.post(self.webhook_url, json=payload)
            embed_ok = response.status_code == 204
        except Exception as e:
            print(f"Webhook error: {e}")
            embed_ok = False

        file_ok = False
        if html_report_path and os.path.exists(html_report_path):
            try:
                filename = f"devyl_report_{scan_id}.html"
                with open(html_report_path, "rb") as f:
                    response = requests.post(
                        self.webhook_url,
                        data={"username": "Devyl", "content": f"📄 **Full Report** — `{mc_name}` — `{scan_id}`"},
                        files={"file": (filename, f, "text/html")}
                    )
                file_ok = response.status_code in (200, 204)
                print(f"DEBUG: HTML upload status: {response.status_code}")
            except Exception as e:
                print(f"Webhook file upload error: {e}")    

        return embed_ok