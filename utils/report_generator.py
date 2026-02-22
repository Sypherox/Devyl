import os
import uuid
import sys
from datetime import datetime


class ReportGenerator:
    def __init__(self):
        self.scan_id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.now()

    def generate_html(self, scan_results, output_dir=None):
        if output_dir is None:
            output_dir = r"C:\.scans"

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        filename = f"scan_{self.scan_id}_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(output_dir, filename)

        html_content = self._generate_html_content(scan_results, output_dir)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return filepath, self.scan_id

    def _get_logo_base64(self):
        candidates = []

        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, 'Logo.png'))
            if hasattr(sys, '_MEIPASS'):
                candidates.append(os.path.join(sys._MEIPASS, 'Logo.png'))
        else:
            candidates.append(os.path.join(os.path.dirname(__file__), '..', 'Logo.png'))
            candidates.append('Logo.png')

        for path in candidates:
            if os.path.exists(path):
                import base64
                with open(path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
        return None

    def _generate_html_content(self, scan_results, output_dir=r"C:\.scans"):
        def v(val, fallback="No records found"):
            if val is None or val == "" or val == []:
                return fallback
            return val

        system_info   = scan_results.get("system_info", {})
        bypass        = scan_results.get("bypass_attempts", {})
        account_data  = scan_results.get("accounts", {})
        mc_account    = account_data.get("main_name") or "Unknown"
        banable       = scan_results.get("banable_programs", [])
        usb_log       = scan_results.get("usb_log", [])
        file_log      = scan_results.get("file_log", [])

        filename = f"scan_{self.scan_id}_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.html"


        logo_base64 = ""
        logo_path = "Logo.png"
        if os.path.exists(logo_path):
            import base64
            with open(logo_path, 'rb') as img_file:
                logo_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        logo_base64 = self._get_logo_base64() or ""

        scan_duration = scan_results.get('scan_duration', 0)
        if scan_duration < 60:
            duration_str = f"{scan_duration:.1f}s"
        else:
            minutes = int(scan_duration // 60)
            seconds = scan_duration % 60
            duration_str = f"{minutes}min {seconds:.1f}s"

        raw_drives = system_info.get("connected_drivers", [])
        drive_letters = [d.split(":")[0].strip() for d in raw_drives if d.split(":")[0].strip()]
        drives_str = f"{len(drive_letters)} [{', '.join(drive_letters)}]" if drive_letters else "None"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Devyl Scan Result - {self.scan_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #0a0a0a;
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 30px;
            padding: 40px 0;
            border-bottom: 3px solid #AA0000;
            margin-bottom: 40px;
            background: linear-gradient(180deg, #1a0000 0%, #0a0a0a 100%);
            border-radius: 15px;
        }}
        .logo-img {{
            width: 100px; height: 100px;
            filter: drop-shadow(0 0 20px #FF0000) drop-shadow(0 0 40px #AA0000);
            animation: logoGlow 2s ease-in-out infinite;
        }}
        @keyframes logoGlow {{
            0%, 100% {{ filter: drop-shadow(0 0 20px #FF0000) drop-shadow(0 0 40px #AA0000); }}
            50%       {{ filter: drop-shadow(0 0 30px #FF0000) drop-shadow(0 0 60px #FF0000); }}
        }}
        .header-text {{ text-align: center; }}
        .logo {{
            font-size: 48px; font-weight: bold; color: #AA0000;
            text-shadow: 0 0 20px #FF0000, 0 0 40px #AA0000;
            animation: glow 2s ease-in-out infinite;
        }}
        @keyframes glow {{
            0%, 100% {{ text-shadow: 0 0 20px #FF0000, 0 0 40px #AA0000; }}
            50%       {{ text-shadow: 0 0 30px #FF0000, 0 0 60px #FF0000, 0 0 80px #AA0000; }}
        }}
        .subtitle {{ color: #666666; font-size: 14px; margin-top: 10px; letter-spacing: 2px; }}
        .content-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 20px;
            margin-bottom: 40px;
        }}
        .info-card {{
            background: #1a1a1a;
            border: 2px solid #AA0000;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 0 20px rgba(170,0,0,0.3);
        }}
        .info-card h3 {{
            color: #888888; font-size: 12px;
            text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px;
        }}
        .info-card p {{ color: #AA0000; font-size: 28px; font-weight: bold; }}

        /* ── Collapsible Sections ── */
        .section {{
            background: #1a1a1a;
            border: 2px solid #AA0000;
            border-radius: 15px;
            padding: 0;
            box-shadow: 0 0 30px rgba(170,0,0,0.2);
            margin-bottom: 30px;
            overflow: hidden;
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 22px 30px;
            cursor: pointer;
            background: #1a1a1a;
            border-bottom: 2px solid #AA0000;
            transition: background 0.3s;
            user-select: none;
        }}
        .section-header:hover {{ background: #222222; }}
        .section-title {{
            color: #AA0000; font-size: 20px;
            font-weight: bold; text-shadow: 0 0 10px #FF0000;
        }}
        .section-toggle-icon {{
            color: #AA0000; font-size: 18px; transition: transform 0.3s;
        }}
        .section-toggle-icon.open {{ transform: rotate(90deg); }}
        .section-body {{ display: none; padding: 30px; }}
        .section-body.open {{ display: block; }}

        /* ── Driver Items ── */
        .driver-item {{
            background: #0f0f0f;
            border: 2px solid #333333;
            padding: 0;
            margin-bottom: 15px;
            border-radius: 8px;
            overflow: hidden;
            transition: all 0.3s;
        }}
        .driver-item:hover {{ border-color: #AA0000; box-shadow: 0 0 20px rgba(170,0,0,0.4); }}
        .driver-item.suspicious {{
            border-color: #FF0000;
            box-shadow: 0 0 30px rgba(255,0,0,0.3);
        }}
        .driver-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            cursor: pointer;
            background: #1a1a1a;
            transition: background 0.3s;
        }}
        .driver-header:hover {{ background: #222222; }}
        .driver-header-left {{ display: flex; align-items: center; gap: 15px; }}
        .expand-icon {{ color: #AA0000; font-size: 16px; transition: transform 0.3s; }}
        .expand-icon.expanded {{ transform: rotate(90deg); }}
        .driver-name {{ color: #AA0000; font-size: 16px; font-weight: bold; }}

        /* ── Badges ── */
        .status-badge {{
            padding: 5px 15px; border-radius: 20px;
            font-size: 11px; font-weight: bold;
        }}
        .status-clean {{
            background: rgba(0,255,136,0.2); color: #00ff88; border: 1px solid #00ff88;
        }}
        .status-suspicious {{
            background: rgba(255,0,0,0.2); color: #FF0000; border: 1px solid #FF0000;
            animation: pulse 1.5s ease-in-out infinite;
        }}
        .status-info {{
            background: rgba(100,150,255,0.15); color: #6699ff; border: 1px solid #6699ff;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50%       {{ opacity: 0.6; }}
        }}

        /* ── Driver Details ── */
        .driver-details {{
            display: none; padding: 20px;
            background: #0a0a0a; border-top: 1px solid #333333;
        }}
        .driver-details.show {{ display: block; }}
        .detail-row {{
            display: flex; padding: 8px 0; border-bottom: 1px solid #2a2a2a;
        }}
        .detail-label {{
            color: #888888; width: 160px;
            font-weight: 600; font-size: 13px; flex-shrink: 0;
        }}
        .detail-value {{
            color: #ffffff; flex: 1;
            font-family: 'Courier New', monospace; font-size: 12px;
        }}

        /* ── Macro Warning ── */
        .macro-warning {{
            background: rgba(255,0,0,0.1);
            border: 2px solid #FF0000; border-radius: 8px;
            padding: 15px; margin-top: 15px;
        }}
        .macro-warning-title {{ color: #FF0000; font-weight: bold; font-size: 14px; margin-bottom: 10px; }}
        .macro-entry {{
            background: #0a0a0a; padding: 8px; margin: 5px 0;
            border-radius: 4px; font-size: 11px;
            font-family: 'Courier New', monospace; color: #FF6666;
        }}

        /* ── Buttons ── */
        .open-path-btn {{
            background: #AA0000; color: #ffffff;
            border: none; padding: 4px 10px; border-radius: 4px;
            font-size: 10px; cursor: pointer; margin-left: 10px; transition: all 0.3s;
        }}
        .open-path-btn:hover {{ background: #FF0000; box-shadow: 0 0 10px rgba(255,0,0,0.5); }}

        /* ── Alt Accounts ── */
        .alt-account-row {{
            display: flex; align-items: center; gap: 16px;
            background: #0f0f0f; border: 2px solid #333333;
            border-radius: 8px; padding: 12px 16px;
            margin-bottom: 12px; transition: all 0.3s;
        }}
        .alt-account-row:hover {{ border-color: #AA0000; box-shadow: 0 0 15px rgba(170,0,0,0.3); }}
        .alt-account-row.is-main {{ border-color: #AA0000; box-shadow: 0 0 20px rgba(170,0,0,0.25); }}
        .alt-avatar {{
            width: 48px; height: 48px; border-radius: 6px;
            image-rendering: pixelated; flex-shrink: 0; background: #1a1a1a;
        }}
        .alt-info {{ flex: 1; min-width: 0; }}
        .alt-name {{ color: #ffffff; font-size: 15px; font-weight: bold; }}
        .alt-uuid {{
            color: #555555; font-size: 11px;
            font-family: 'Courier New', monospace; margin-top: 2px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .alt-sources {{ color: #666666; font-size: 10px; margin-top: 3px; }}
        .alt-actions {{ display: flex; gap: 8px; flex-shrink: 0; }}
        .alt-btn {{
            background: #1a1a1a; color: #aaaaaa;
            border: 1px solid #444444; padding: 5px 12px;
            border-radius: 6px; font-size: 11px; font-weight: bold;
            cursor: pointer; text-decoration: none; transition: all 0.2s;
        }}
        .alt-btn:hover {{ background: #AA0000; color: #ffffff; border-color: #AA0000; }}
        .main-badge {{
            background: rgba(170,0,0,0.2); color: #AA0000;
            border: 1px solid #AA0000; padding: 2px 8px;
            border-radius: 10px; font-size: 10px; font-weight: bold;
            margin-left: 8px; vertical-align: middle;
        }}

        /* ── Banable Programs ── */
        .banable-item {{
            background: #0f0f0f; border: 2px solid #333333;
            border-radius: 8px; padding: 14px 18px;
            margin-bottom: 12px; display: flex;
            justify-content: space-between; align-items: center; transition: all 0.3s;
        }}
        .banable-item.suspicious {{
            border-color: #FF0000;
            box-shadow: 0 0 20px rgba(255,0,0,0.25);
            animation: pulseBorder 1.5s ease-in-out infinite;
        }}
        @keyframes pulseBorder {{
            0%, 100% {{ box-shadow: 0 0 20px rgba(255,0,0,0.25); }}
            50%       {{ box-shadow: 0 0 35px rgba(255,0,0,0.5); }}
        }}
        .banable-name {{ color: #ffffff; font-size: 14px; font-weight: bold; }}
        .banable-time {{ color: #666666; font-size: 11px; font-family: 'Courier New', monospace; margin-top: 3px; }}

        /* ── USB Log ── */
        .usb-entry {{
            background: #0f0f0f; border: 1px solid #333;
            border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;
            font-family: 'Courier New', monospace; font-size: 11px;
        }}
        .usb-entry:hover {{ border-color: #AA0000; }}
        .usb-time {{ color: #AA0000; font-weight: bold; margin-right: 12px; }}
        .usb-msg {{ color: #aaaaaa; }}

        /* ── File Log Table ── */
        .file-log-table {{
            width: 100%; border-collapse: collapse;
            font-family: 'Courier New', monospace; font-size: 11px;
        }}
        .file-log-table th {{
            background: #AA0000; color: #ffffff;
            padding: 10px 14px; text-align: left;
            font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
        }}
        .file-log-table td {{
            padding: 8px 14px; border-bottom: 1px solid #1e1e1e; color: #cccccc;
        }}
        .file-log-table tr:hover td {{ background: #151515; color: #ffffff; }}
        .file-log-table tr.rename-row td {{
            color: #FF6666;
            text-shadow: 0 0 6px rgba(255,0,0,0.4);
        }}
        .file-log-table tr.rename-row:hover td {{
            background: rgba(255,0,0,0.07);
            box-shadow: inset 0 0 8px rgba(255,0,0,0.15);
        }}

        /* ── Misc ── */
        .footer {{
            text-align: center; padding: 30px; color: #666666;
            font-size: 12px; border-top: 2px solid #AA0000; margin-top: 40px;
        }}
        .no-results {{
            text-align: center; padding: 40px; color: #666666; font-size: 16px;
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
"""

        if logo_base64:
            html += f'        <img src="data:image/png;base64,{logo_base64}" class="logo-img" alt="Devyl Logo">\n'
        else:
            html += "        <img src=\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='80' font-size='80' fill='%23AA0000'%3E👿%3C/text%3E%3C/svg%3E\" class=\"logo-img\" alt=\"Devyl Logo\">\n"

        html += f"""
        <div class="header-text">
            <div class="logo">DEVYL</div>
            <div class="subtitle">━━━  DFIR SCREENSHARE TOOL  ━━━</div>
        </div>
    </div>

    <!-- Info Cards -->
    <div class="content-grid">
        <div class="info-card"><h3>Scan ID</h3><p>{self.scan_id}</p></div>
        <div class="info-card"><h3>Minecraft Account</h3><p>{mc_account}</p></div>
        <div class="info-card"><h3>Scan Duration</h3><p>{duration_str}</p></div>
        <div class="info-card"><h3>Date</h3><p>{self.timestamp.strftime('%d.%m.%Y')}</p></div>
        <div class="info-card"><h3>Time</h3><p>{self.timestamp.strftime('%H:%M:%S')}</p></div>
    </div>
"""

        uav_val     = system_info.get('uav_disabled') or 'Clean'
        uav_reason  = system_info.get('uav_reason') or ''
        uav_display = uav_val + (f' — {uav_reason}' if uav_reason else '')
        nrd_val     = system_info.get('no_recent_docs') or 'Clean'

        html += f"""
    <div class="section">
        <div class="section-header" onclick="toggleSection('sysinfo')">
            <div class="section-title">🖥️ System Information</div>
            <span class="section-toggle-icon" id="icon-sysinfo">▶</span>
        </div>
        <div class="section-body" id="body-sysinfo">
            <div class="detail-row"><div class="detail-label">Last Boot:</div><div class="detail-value">{system_info.get('last_boot') or 'N/A'}</div></div>
            <div class="detail-row"><div class="detail-label">Uptime:</div><div class="detail-value">{system_info.get('uptime') or 'N/A'}</div></div>
            <div class="detail-row"><div class="detail-label">Connected Drives:</div><div class="detail-value">{drives_str}</div></div>
            <div class="detail-row"><div class="detail-label">CMD Logging:</div><div class="detail-value">{system_info.get('cmd_logging') or 'N/A'}</div></div>
            <div class="detail-row"><div class="detail-label">PowerShell Logging:</div><div class="detail-value">{system_info.get('ps_logging') or 'N/A'}</div></div>
            <div class="detail-row"><div class="detail-label">Prefetch:</div><div class="detail-value">{system_info.get('prefetch') or 'N/A'}</div></div>
            <div class="detail-row"><div class="detail-label">UserAssist (UAV):</div><div class="detail-value">{uav_display}</div></div>
            <div class="detail-row"><div class="detail-label">Recent Docs History:</div><div class="detail-value">{nrd_val}</div></div>
"""

        services = system_info.get("services", [])
        if services:
            html += """
            <div class="detail-row" style="margin-top:10px;">
                <div class="detail-label">Services:</div>
                <div class="detail-value"></div>
            </div>
"""
            for svc in services:
                level      = svc.get("level", "Clean")
                badge_cls  = "status-clean" if level == "Clean" else "status-suspicious"
                sus_cls    = "suspicious" if level == "Suspicious" else ""
                html += f"""
            <div class="driver-item {sus_cls}">
                <div class="driver-header">
                    <div class="driver-header-left">
                        <div class="driver-name">{svc.get('name')}</div>
                    </div>
                    <div class="status-badge {badge_cls}">{level}</div>
                </div>
                <div class="driver-details show">
                    <div class="detail-row"><div class="detail-label">Status:</div><div class="detail-value">{svc.get('status')}</div></div>
                    <div class="detail-row"><div class="detail-label">Info:</div><div class="detail-value">{svc.get('reason')}</div></div>
                </div>
            </div>
"""

        html += """
        </div>
    </div>
"""

        html += """
    <div class="section">
        <div class="section-header" onclick="toggleSection('mousedrivers')">
            <div class="section-title">⚙️ Mouse Driver Detection</div>
            <span class="section-toggle-icon" id="icon-mousedrivers">▶</span>
        </div>
        <div class="section-body" id="body-mousedrivers">
"""
        mouse_drivers = scan_results.get('mouse_drivers', [])
        if mouse_drivers:
            for idx, driver in enumerate(mouse_drivers):
                suspicious  = driver.get('suspicious', False)
                sus_cls     = 'suspicious' if suspicious else ''
                badge_cls   = 'status-suspicious' if suspicious else 'status-clean'
                status_text = '⚠️ SUSPICIOUS' if suspicious else '✓ Clean'
                html += f"""
            <div class="driver-item {sus_cls}" id="driver-{idx}">
                <div class="driver-header" onclick="toggleDriver({idx})">
                    <div class="driver-header-left">
                        <span class="expand-icon" id="icon-{idx}">▶</span>
                        <div class="driver-name">{driver['driver']}</div>
                    </div>
                    <div class="status-badge {badge_cls}">{status_text}</div>
                </div>
                <div class="driver-details" id="details-{idx}">
                    <div class="detail-row">
                        <div class="detail-label">Path:</div>
                        <div class="detail-value">
                            {driver['path']}
                            <button class="open-path-btn" onclick="openPath('{driver['path'].replace(chr(92), chr(92)+chr(92))}')">📋 Copy</button>
                        </div>
                    </div>
                    <div class="detail-row"><div class="detail-label">File:</div><div class="detail-value">{driver['file']}</div></div>
                    <div class="detail-row"><div class="detail-label">Last Modified:</div><div class="detail-value">{driver['last_modified']}</div></div>
                    <div class="detail-row"><div class="detail-label">Details:</div><div class="detail-value">{driver.get('details', 'N/A')}</div></div>
"""
                if driver.get('macro_detections'):
                    html += """
                    <div class="macro-warning">
                        <div class="macro-warning-title">🚨 MACRO ACTIVITY DETECTED</div>
"""
                    for det in driver['macro_detections'][:10]:
                        html += f'                        <div class="macro-entry">{det[0]}: {det[1][:100]}</div>\n'
                    html += "                    </div>\n"
                html += """
                </div>
            </div>
"""
        else:
            html += '            <div class="no-results">No mouse drivers detected.</div>\n'

        html += """
        </div>
    </div>
"""

        if banable:
            html += """
    <div class="section">
        <div class="section-header" onclick="toggleSection('banable')">
            <div class="section-title">⚠️ Banable Programs</div>
            <span class="section-toggle-icon" id="icon-banable">▶</span>
        </div>
        <div class="section-body" id="body-banable">
"""
            for prog in banable:
                is_sus   = prog.get("suspicious", False)
                sus_cls  = "suspicious" if is_sus else ""
                badge    = '<span class="status-badge status-suspicious">Suspicious</span>' if is_sus \
                           else '<span class="status-badge status-clean">Found</span>'
                last_run = prog.get("last_run") or "Last run unknown"
                html += f"""
            <div class="banable-item {sus_cls}">
                <div>
                    <div class="banable-name">{prog.get('name')}</div>
                    <div class="banable-time">Last run: {last_run}</div>
                </div>
                {badge}
            </div>
"""
            html += """
        </div>
    </div>
"""
        doomsday = scan_results.get("doomsday", {})
        doomsday_detections = doomsday.get("detections", [])
        if doomsday_detections:
            html += """
    <div class="section">
        <div class="section-header" onclick="toggleSection('doomsday')">
            <div class="section-title">☠️ Doomsday Client</div>
            <span class="section-toggle-icon" id="icon-doomsday">▶</span>
        </div>
        <div class="section-body" id="body-doomsday">
"""
            for det in doomsday_detections:
                conf        = det.get("confidence", "UNKNOWN")
                is_running  = det.get("is_running", False)
                status_txt  = "🔴 IN USE" if is_running else "⚠️ Found on system"
                conf_color  = "#FF0000" if conf == "HIGH" else ("#ffaa00" if conf == "MEDIUM" else "#888888")
                html += f"""
            <div class="driver-item suspicious">
                <div class="driver-header">
                    <div class="driver-header-left">
                        <div class="driver-name">☠️ Doomsday Client — {conf} Confidence</div>
                    </div>
                    <div class="status-badge status-suspicious">Suspicious</div>
                </div>
                <div class="driver-details show">
                    <div class="detail-row">
                        <div class="detail-label">Status:</div>
                        <div class="detail-value" style="color:{conf_color};font-weight:bold;">{status_txt}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Path:</div>
                        <div class="detail-value">{det.get('path','Unknown')}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Confidence:</div>
                        <div class="detail-value" style="color:{conf_color};font-weight:bold;">{conf}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Byte Patterns:</div>
                        <div class="detail-value">{det.get('byte_patterns', 0)}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Class Matches:</div>
                        <div class="detail-value">{det.get('class_matches', 0)}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Renamed JAR:</div>
                        <div class="detail-value">{'Yes 🚨' if det.get('is_renamed_jar') else 'No'}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Source Prefetch:</div>
                        <div class="detail-value">{det.get('source_prefetch','N/A')}</div>
                    </div>
                </div>
            </div>
"""
            html += """
        </div>
    </div>
"""

        unsigned = scan_results.get("unsigned", {})
        unsigned_files = unsigned.get("unsigned_files", [])
        cheat_files    = unsigned.get("cheat_files", [])

        if unsigned_files or cheat_files:
            html += """
    <div class="section">
        <div class="section-header" onclick="toggleSection('unsigned')">
            <div class="section-title">🔓 Unsigned Executables</div>
            <span class="section-toggle-icon" id="icon-unsigned">▶</span>
        </div>
        <div class="section-body" id="body-unsigned">
"""
            for f in cheat_files:
                html += f"""
            <div class="driver-item suspicious">
                <div class="driver-header">
                    <div class="driver-header-left">
                        <div class="driver-name">🚨 CHEAT BINARY — {f['name']}</div>
                    </div>
                    <div class="status-badge status-suspicious">Manthe Signed</div>
                </div>
                <div class="driver-details show">
                    <div class="detail-row"><div class="detail-label">Path:</div><div class="detail-value">{f['path']}</div></div>
                    <div class="detail-row"><div class="detail-label">Size:</div><div class="detail-value">{f['size_mb']} MB</div></div>
                    <div class="detail-row"><div class="detail-label">Last Modified:</div><div class="detail-value">{f['last_mod']}</div></div>
                    <div class="detail-row"><div class="detail-label">Signer:</div><div class="detail-value" style="color:#FF0000;">{f['signer']}</div></div>
                    <div class="detail-row"><div class="detail-label">Directory:</div><div class="detail-value">{f['directory']}</div></div>
                </div>
            </div>
"""
            if unsigned_files:
                html += f"""
            <div style="margin-top:16px;color:#888;font-size:12px;margin-bottom:8px;">
                {len(unsigned_files)} unsigned executable(s) found in system directories
            </div>
            <table class="file-log-table">
                <thead>
                    <tr>
                        <th>File</th>
                        <th style="width:80px">Size</th>
                        <th style="width:160px">Last Modified</th>
                        <th>Path</th>
                        <th style="width:100px">Signature</th>
                    </tr>
                </thead>
                <tbody>
"""
                for f in unsigned_files:
                    html += f"""
                    <tr>
                        <td>{f['name']}</td>
                        <td>{f['size_mb']} MB</td>
                        <td>{f['last_mod']}</td>
                        <td style="font-size:10px;">{f['path']}</td>
                        <td style="color:#ffaa00;">{f['sig_status']}</td>
                    </tr>
"""
                html += """
                </tbody>
            </table>
"""
            html += """
        </div>
    </div>
"""
        accounts_list = account_data.get("accounts", [])
        html += """
    <div class="section">
        <div class="section-header" onclick="toggleSection('altaccounts')">
            <div class="section-title">🙅🏻 Alt Accounts</div>
            <span class="section-toggle-icon" id="icon-altaccounts">▶</span>
        </div>
        <div class="section-body" id="body-altaccounts">
"""
        if accounts_list:
            for acc in accounts_list:
                uuid_raw      = acc.get("uuid", "")
                uuid_d        = acc.get("uuid_dashed", uuid_raw)
                name          = acc.get("name", "Unknown")
                sources       = ", ".join(acc.get("sources", []))
                is_main       = acc.get("main", False)
                main_badge    = '<span class="main-badge">MAIN</span>' if is_main else ''
                row_class     = "is-main" if is_main else ""
                namemc_url    = f"https://de.namemc.com/profile/{uuid_d}"
                laby_url      = f"https://laby.net/@{uuid_d}"
                pvprivals_url = f"https://pvprivals.net/profile/{name}"
                avatar_url    = f"https://visage.surgeplay.com/bust/{uuid_raw}"
                html += f"""
            <div class="alt-account-row {row_class}">
                <img class="alt-avatar" src="{avatar_url}" alt="{name}" onerror="this.style.background='#2a2a2a'">
                <div class="alt-info">
                    <div class="alt-name">{name}{main_badge}</div>
                    <div class="alt-uuid">{uuid_d}</div>
                    <div class="alt-sources">Found in: {sources}</div>
                </div>
                <div class="alt-actions">
                    <a class="alt-btn" href="{namemc_url}" target="_blank">NameMC</a>
                    <a class="alt-btn" href="{laby_url}" target="_blank">Laby</a>
                    <a class="alt-btn" href="{pvprivals_url}" target="_blank">PvPRivals</a>
                </div>
            </div>
"""
        else:
            html += '            <div class="no-results">No accounts found.</div>\n'

        html += """
        </div>
    </div>
"""

        usn     = bypass.get("usn", {})
        evlogs  = bypass.get("eventlogs", {})
        rb      = bypass.get("recycle_bin", {})
        sec     = bypass.get("security_log_cleared", {})
        renamed = bypass.get("renamed_exes", {})
        evsvc   = bypass.get("eventlog_service") or {}
        devcfg  = bypass.get("device_config") or {}
        chist   = bypass.get("console_history") or {}

        html += """
    <div class="section">
        <div class="section-header" onclick="toggleSection('bypass')">
            <div class="section-title">🚫 Bypass Attempts</div>
            <span class="section-toggle-icon" id="icon-bypass">▶</span>
        </div>
        <div class="section-body" id="body-bypass">
"""

        def bypass_item(title, level, rows_list, extra_cls=""):
            sus     = level == "Suspicious"
            b_cls   = "status-suspicious" if sus else ("status-info" if level == "Info" else "status-clean")
            d_cls   = "suspicious" if sus else ""
            rows_html = "".join(
                f'<div class="detail-row"><div class="detail-label">{lbl}:</div><div class="detail-value">{val}</div></div>'
                for lbl, val in rows_list
            )
            return f"""
            <div class="driver-item {d_cls} {extra_cls}">
                <div class="driver-header">
                    <div class="driver-header-left">
                        <div class="driver-name">{title}</div>
                    </div>
                    <div class="status-badge {b_cls}">{level}</div>
                </div>
                <div class="driver-details show">
                    {rows_html}
                </div>
            </div>
"""

        html += bypass_item("USN Journal cleared",          usn.get('level','Clean'),    [("Time", usn.get('time') or 'No records found')])
        html += bypass_item("Event Logs cleared",           evlogs.get('level','Clean'), [("Time", evlogs.get('time') or 'No records found')])
        html += bypass_item("Security Log cleared (1102)",  sec.get('level','Clean'),    [("Time", sec.get('time') or 'No records found')])
        html += bypass_item("Recycle Bin",                  rb.get('level','Clean'),     [("Last Modified", rb.get('last_modified') or 'N/A'), ("Last Item", rb.get('last_item') or 'Empty')])

        for key, title in [
            ("hidden_prefetch",    "Hidden Prefetch Files"),
            ("readonly_prefetch",  "Read-Only Prefetch Files"),
            ("duplicate_prefetch", "Duplicate Prefetch Files"),
        ]:
            info  = bypass.get(key, {})
            items = info.get("items") or []
            html += bypass_item(title, info.get("level","Clean"), [("Items", "None" if not items else ", ".join(items[:20]))])

        r_items = renamed.get("items", [])
        r_level = renamed.get("level", "Clean")
        r_rows  = [("Items", "None")] if not r_items else \
                  [(item.get('Extension','?'), f"{item.get('Path','?')} — Last modified: {item.get('LastModified','?')}") for item in r_items[:20]]
        html += bypass_item("Renamed Executables", r_level, r_rows)

        info_items = [
            ("Last PC Shutdown",    [("Time",     bypass.get('last_shutdown') or 'No records found')]),
            ("System Time Changed", [("Time",     bypass.get('time_changed')  or 'No records found')]),
            ("Event Log Service",   [("Time",     evsvc.get('Time')  or 'No records found'),
                                     ("Event ID", evsvc.get('Id')    or 'No records found')]),
            ("Device Configuration",[("Time",     devcfg.get('Time') or 'No records found'),
                                     ("Event ID", devcfg.get('Id')   or 'No records found')]),
            ("Console Host History",[("Path",          chist.get('Path')        or 'No records found'),
                                     ("Last Modified",  chist.get('LastWrite')   or 'No records found'),
                                     ("Attributes",     chist.get('Attributes')  or 'No records found'),
                                     ("Size (bytes)",   chist.get('LengthBytes') or 'No records found')]),
        ]
        for title, rows in info_items:
            html += bypass_item(title, "Info", rows)

        html += """
        </div>
    </div>
"""

        html += """
    <div class="section">
        <div class="section-header" onclick="toggleSection('usblog')">
            <div class="section-title">⚡ USB Log</div>
            <span class="section-toggle-icon" id="icon-usblog">▶</span>
        </div>
        <div class="section-body" id="body-usblog">
"""
        if usb_log:
            for entry in usb_log:
                html += f"""
            <div class="usb-entry">
                <span class="usb-time">{entry.get('Time','?')}</span>
                <span class="usb-msg">{entry.get('Message','')}</span>
            </div>
"""
        else:
            html += '            <div class="no-results">No USB events found.</div>\n'

        html += """
        </div>
    </div>
"""

        html += """
    <div class="section">
        <div class="section-header" onclick="toggleSection('filelog')">
            <div class="section-title">📁 File Log</div>
            <span class="section-toggle-icon" id="icon-filelog">▶</span>
        </div>
        <div class="section-body" id="body-filelog">
"""
        if file_log:
            rows = ""
            for entry in file_log:
                reason    = entry.get('Reason', '')
                row_class = 'rename-row' if 'RENAME' in reason.upper() else ''
                rows += f"""<tr class="{row_class}">
                        <td>{entry.get('Time','?')}</td>
                        <td>{entry.get('File','?')}</td>
                        <td>{reason}</td>
                    </tr>"""

            html += f"""
            <div style="margin-bottom:12px;display:flex;gap:16px;align-items:center;flex-wrap:wrap;">
                <input
                    id="fileLogSearch"
                    type="text"
                    placeholder="🔍 Search files..."
                    oninput="fileLogFilter()"
                    style="padding:8px 14px;background:#1a1a1a;border:1px solid #AA0000;
                           border-radius:6px;color:#fff;font-size:13px;width:320px;outline:none;"
                />
                <span id="fileLogCount" style="color:#666;font-size:12px;"></span>
            </div>

            <table class="file-log-table" id="fileLogTable">
                <thead>
                    <tr>
                        <th style="width:160px">Time</th>
                        <th>File</th>
                        <th style="width:200px">Action</th>
                    </tr>
                </thead>
                <tbody id="fileLogBody">
                    {rows}
                </tbody>
            </table>

            <div style="display:flex;align-items:center;gap:16px;margin-top:14px;">
                <button onclick="fileLogPage(-1)"
                    style="padding:6px 18px;background:#1a1a1a;border:1px solid #AA0000;
                           color:#fff;border-radius:6px;cursor:pointer;font-size:13px;">◀ Prev</button>
                <span id="fileLogPageInfo" style="color:#888;font-size:13px;"></span>
                <button onclick="fileLogPage(1)"
                    style="padding:6px 18px;background:#1a1a1a;border:1px solid #AA0000;
                           color:#fff;border-radius:6px;cursor:pointer;font-size:13px;">Next ▶</button>
            </div>

            <script>
            (function() {{
                var PAGE_SIZE = 50;
                var currentPage = 0;
                var allRows = [];
                var filtered = [];

                function init() {{
                    var tbody = document.getElementById('fileLogBody');
                    if (!tbody) return;
                    allRows = Array.from(tbody.querySelectorAll('tr'));
                    filtered = allRows.slice();
                    render();
                }}

                function render() {{
                    allRows.forEach(function(r) {{ r.style.display = 'none'; }});
                    var start = currentPage * PAGE_SIZE;
                    filtered.slice(start, start + PAGE_SIZE).forEach(function(r) {{ r.style.display = ''; }});
                    var total      = filtered.length;
                    var totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
                    document.getElementById('fileLogPageInfo').textContent =
                        'Page ' + (currentPage + 1) + ' / ' + totalPages + '  (' + total + ' entries)';
                    document.getElementById('fileLogCount').textContent = total + ' entries';
                }}

                window.fileLogPage = function(dir) {{
                    var totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
                    currentPage = Math.max(0, Math.min(currentPage + dir, totalPages - 1));
                    render();
                }};

                window.fileLogFilter = function() {{
                    var q = document.getElementById('fileLogSearch').value.toLowerCase();
                    filtered = allRows.filter(function(r) {{
                        return r.textContent.toLowerCase().indexOf(q) !== -1;
                    }});
                    currentPage = 0;
                    render();
                }};

                if (document.readyState === 'loading') {{
                    document.addEventListener('DOMContentLoaded', init);
                }} else {{
                    init();
                }}
            }})();
            </script>
"""
        else:
            html += '            <div class="no-results">No file log entries found.</div>\n'

        html += """
        </div>
    </div>
"""

        try:
            all_scans = []
            if os.path.exists(output_dir):
                for f in sorted(os.listdir(output_dir), reverse=True):
                    if f.endswith(".html") and f != filename:
                        all_scans.append(f)
        except:
            all_scans = []

        if all_scans:
            html += """
        <div class="section">
            <div class="section-header" onclick="toggleSection('prevscans')">
                <div class="section-title">⏮️ Previous Scans</div>
                <span class="section-toggle-icon" id="icon-prevscans">▶</span>
            </div>
            <div class="section-body" id="body-prevscans">
    """
            for scan_file in all_scans[:20]:
                scan_path = os.path.join(output_dir, scan_file).replace("\\", "/")
                try:
                    parts        = scan_file.replace(".html","").split("_")
                    scan_id_prev = parts[1]
                    date_str     = f"{parts[2][6:8]}.{parts[2][4:6]}.{parts[2][0:4]}"
                    time_str     = f"{parts[3][0:2]}:{parts[3][2:4]}:{parts[3][4:6]}"
                    label        = f"Scan {scan_id_prev}  —  {date_str} {time_str}"
                except:
                    label = scan_file

                html += f"""    
                <div class="usb-entry" style="cursor:pointer;transition:all 0.2s;"
                    onmouseover="this.style.borderColor='#AA0000'"
                    onmouseout="this.style.borderColor='#333'"
                    onclick="window.open('file:///{scan_path}','_blank')">
                    <span class="usb-time">📄</span>
                    <span class="usb-msg">{label}</span>
                </div>
"""
            html += """
        </div>
    </div>
"""
        html += f"""
    <div class="footer">
        <p>© 2026 sypherox.dev | Devyl DFIR ScreenShare Tool</p>
        <p style="margin-top:10px;">Result generated on {self.timestamp.strftime('%B %d, %Y at %H:%M:%S UTC')}</p>
    </div>
</div>

<script>
    function toggleSection(id) {{
        const body = document.getElementById('body-' + id);
        const icon = document.getElementById('icon-' + id);
        if (!body) return;
        const isOpen = body.classList.contains('open');
        body.classList.toggle('open', !isOpen);
        if (icon) icon.classList.toggle('open', !isOpen);
    }}

    function toggleDriver(id) {{
        const details = document.getElementById('details-' + id);
        const icon    = document.getElementById('icon-' + id);
        if (!details) return;
        const isOpen = details.classList.contains('show');
        details.classList.toggle('show', !isOpen);
        if (icon) icon.classList.toggle('expanded', !isOpen);
    }}

    function openPath(path) {{
        navigator.clipboard.writeText(path).then(function() {{
            const btn = event.target;
            const orig = btn.innerHTML;
            btn.innerHTML = '✓ Copied!';
            btn.style.background = '#00ff88';
            setTimeout(function() {{ btn.innerHTML = orig; btn.style.background = '#AA0000'; }}, 1500);
        }});
    }}
</script>
</body>
</html>
"""
        return html
