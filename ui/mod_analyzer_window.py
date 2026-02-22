import customtkinter as ctk
from scanner.mod_scanner import ModScanner
import threading


class ModAnalyzerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Mod Analyzer")
        self.geometry("700x500")
        self.configure(fg_color="#0a0a0a")
        self.resizable(False, False)

        ctk.CTkLabel(
            self, text="🎮 MOD ANALYZER",
            font=ctk.CTkFont(family="Minecraft", size=22, weight="bold"),
            text_color="#AA0000"
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self, text="Scans .jar mods for known cheat signatures",
            text_color="#666666", font=ctk.CTkFont(size=12)
        ).pack(pady=(0, 15))

        path_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=8)
        path_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            path_frame, text="Mods Folder:",
            text_color="#888888", font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=10, pady=10)

        self.path_entry = ctk.CTkEntry(
            path_frame, width=400,
            placeholder_text=r"%AppData%\.minecraft\mods",
            fg_color="#0f0f0f", border_color="#AA0000",
            text_color="#ffffff"
        )
        self.path_entry.pack(side="left", padx=5, pady=10, fill="x", expand=True)

        self.scan_btn = ctk.CTkButton(
            self, text="▶  Start Scan",
            command=self._start_scan,
            fg_color="#AA0000", hover_color="#FF0000",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Minecraft", size=14, weight="bold"),
            height=40, width=200
        )
        self.scan_btn.pack(pady=10)

        self.status_label = ctk.CTkLabel(
            self, text="", text_color="#888888",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack()

        self.result_box = ctk.CTkTextbox(
            self, width=660, height=300,
            fg_color="#0f0f0f", text_color="#cccccc",
            font=ctk.CTkFont(family="Courier New", size=11),
            border_color="#333333", border_width=1
        )
        self.result_box.pack(padx=20, pady=10)
        self.result_box.configure(state="disabled")

    def _start_scan(self):
        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.status_label.configure(text="⏳ Scanning mods folder...")
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.configure(state="disabled")

        mods_path = self.path_entry.get().strip()

        def worker():
            scanner = ModScanner()
            results = scanner.run(mods_path=mods_path)
            self.after(0, lambda: self._show_results(results))

        threading.Thread(target=worker, daemon=True).start()

    def _show_results(self, results: dict):
        self.scan_btn.configure(state="normal", text="▶  Start Scan")

        if results.get("error") and not results.get("path_exists"):
            self.status_label.configure(
                text=f"❌ {results['error']}", text_color="#FF0000"
            )
            return

        lines = []

        if results.get("minecraft_running"):
            lines.append(f"✓ Minecraft running — started {results['mc_start_time']} (uptime: {results['mc_uptime']})")
            lines.append("")

        lines.append(f"📂 Mods folder: {results['mods_path']}")
        lines.append(f"   Verified: {len(results['verified_mods'])}  |  Unknown: {len(results['unknown_mods'])}  |  Cheats: {len(results['cheat_mods'])}")
        lines.append("")

        if results["cheat_mods"]:
            lines.append("━━━  🚨 CHEAT MODS DETECTED  ━━━")
            for m in results["cheat_mods"]:
                dep = f" → {m['dep_file']}" if m["dep_file"] else ""
                lines.append(f"  ⛔ {m['file_name']}{dep}")
                lines.append(f"     Strings: {', '.join(m['strings_found'])}")
                if m["zone_id"]:
                    lines.append(f"     Source URL: {m['zone_id']}")
            lines.append("")

        if results["unknown_mods"]:
            lines.append("━━━  ⚠️ UNKNOWN MODS  ━━━")
            for m in results["unknown_mods"]:
                zone = f"  ← {m['zone_id']}" if m["zone_id"] else ""
                lines.append(f"  ? {m['file_name']} ({m['size_mb']} MB){zone}")
            lines.append("")

        if results["verified_mods"]:
            lines.append("━━━  ✓ VERIFIED MODS  ━━━")
            for m in results["verified_mods"]:
                lines.append(f"  ✓ {m['mod_name']}  [{m['file_name']}]  via {m['source']}")

        status_color = "#FF0000" if results["has_cheats"] else (
            "#ffaa00" if results["unknown_mods"] else "#00ff88"
        )
        status_text = (
            f"🚨 {len(results['cheat_mods'])} cheat mod(s) detected!" if results["has_cheats"]
            else f"⚠️ {len(results['unknown_mods'])} unknown mod(s)" if results["unknown_mods"]
            else "✓ All mods verified clean"
        )
        self.status_label.configure(text=status_text, text_color=status_color)

        self.result_box.configure(state="normal")
        self.result_box.insert("1.0", "\n".join(lines))
        self.result_box.configure(state="disabled")
