import customtkinter as ctk
from PIL import Image, ImageFilter, ImageEnhance
import os
import sys
import math

try:
    from config import ACCESS_CODE
except ImportError:
    print("ERROR: config.py not found!")
    print("Please copy config.example.py to config.py and configure it.")
    ACCESS_CODE = None

import tkinter.font as tkfont
from pathlib import Path

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def load_custom_font(font_path):
    try:
        from ctypes import windll, byref, create_unicode_buffer, create_string_buffer
        FR_PRIVATE = 0x10
        FR_NOT_ENUM = 0x20
        
        if os.path.exists(font_path):
            windll.gdi32.AddFontResourceExW(
                byref(create_unicode_buffer(font_path)), 
                FR_PRIVATE, 
                0
            )
            print(f"✓ Minecraft Font geladen: {font_path}")
            return True
    except Exception as e:
        print(f"Font loading error: {e}")
    return False

MINECRAFT_FONT_LOADED = False
for font_name in ["Minecraft.ttf", "Minecrafter.Reg.ttf", "Minecraftia.ttf"]:
    font_path = get_resource_path(font_name)
    if os.path.exists(font_path):
        if load_custom_font(os.path.abspath(font_path)):
            MINECRAFT_FONT_LOADED = True
            break

class DevylApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("𝕯𝖊𝖛𝖞𝖑")
        self.geometry("800x950")
        self.resizable(False, False)
        
        icon_path = get_resource_path("Logo.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
                print(f"✓ Icon geladen: {icon_path}")
            except Exception as e:
                print(f"Icon error: {e}")
        
        ctk.set_appearance_mode("dark")
        self.configure(fg_color="#0a0a0a")
        
        self.RED_NEON = "#AA0000"
        self.RED_GLOW = "#FF0000"
        self.RED_DARK = "#660000"
        self.BG_DARK = "#0a0a0a"
        self.BG_CARD = "#1a1a1a"
        
        self.glow_time = 0
        self.animation_running = True
        self.scan_logs = True 
        
        self.setup_ui()
        self.animate_glow()
    
    def create_glowing_logo(self):
        logo_path = get_resource_path("Logo.png")
        
        if not os.path.exists(logo_path):
            print(f"WARNING: Logo not found: {logo_path}")
            return None
        
        try:
            logo = Image.open(logo_path)
            logo = logo.resize((120, 120), Image.Resampling.LANCZOS)
            
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            
            glow = logo.copy()
            for i in range(3):
                glow = glow.filter(ImageFilter.GaussianBlur(radius=15))
            
            enhancer = ImageEnhance.Brightness(glow)
            glow = enhancer.enhance(1.5)
            
            final = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
            final.paste(glow, (20, 20), glow)
            final.paste(logo, (20, 20), logo)
            
            print(f"✓ Logo geladen: {logo_path}")
            return ctk.CTkImage(
                light_image=final,
                dark_image=final,
                size=(160, 160)
            )
        except Exception as e:
            print(f"Logo error: {e}")
            return None
    
    def setup_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=40, pady=40)

        logo_image = self.create_glowing_logo()
        if logo_image:
            logo_container = ctk.CTkFrame(main_frame, fg_color="transparent")
            logo_container.pack(pady=(0, 15), fill="x")
            self.logo_label = ctk.CTkLabel(logo_container, image=logo_image, text="")
            self.logo_label.pack()

        title_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_container.pack(pady=(0, 5), fill="x")
        self.title_label = ctk.CTkLabel(
            title_container,
            text="DEVYL",
            font=("Arial Black", 56, "bold"),
            text_color=self.RED_NEON
        )
        self.title_label.pack()

        subtitle = ctk.CTkLabel(
            main_frame,
            text="━━━  DFIR SCREENSHARE TOOL  ━━━",
            font=("Consolas", 14, "bold"),
            text_color="#666666"
        )
        subtitle.pack(pady=(0, 20))

        tools_label = ctk.CTkLabel(
            main_frame,
            text="━━━  QUICK TOOLS  ━━━",
            font=("Consolas", 11, "bold"),
            text_color="#444444"
        )
        tools_label.pack(pady=(0, 8))

        tools_row = ctk.CTkFrame(main_frame, fg_color="transparent")
        tools_row.pack(pady=(0, 20))

        btn_style = dict(
            height=38, font=("Arial", 12, "bold"),
            fg_color="#1a1a1a", hover_color="#AA0000",
            text_color="#ffffff", border_width=2,
            border_color="#AA0000", corner_radius=8
        )

        ctk.CTkButton(tools_row, text="👁 Show hidden files", width=200,
                      command=self._run_show_hidden_files, **btn_style).pack(side="left", padx=6)
        ctk.CTkButton(tools_row, text="🎮 Mod Analyzer",      width=180,
                      command=self._open_mod_analyzer,     **btn_style).pack(side="left", padx=6)
        ctk.CTkButton(tools_row, text="🖱 Mouse Tracker",     width=180,
                      command=self._open_mouse_tracker,    **btn_style).pack(side="left", padx=6)

        self.outer_glow_frame = ctk.CTkFrame(main_frame, fg_color="transparent", corner_radius=18)
        self.outer_glow_frame.pack(pady=10, padx=60, fill="x")

        self.card_frame = ctk.CTkFrame(
            self.outer_glow_frame,
            fg_color=self.BG_CARD, corner_radius=15,
            border_width=3, border_color=self.RED_NEON
        )
        self.card_frame.pack(padx=3, pady=3, fill="x")

        card_content = ctk.CTkFrame(self.card_frame, fg_color="transparent")
        card_content.pack(padx=40, pady=30)

        ctk.CTkLabel(card_content, text="ACCESS CODE",
                     font=("Arial", 14, "bold"), text_color="#888888").pack(pady=(0, 10))

        self.entry_outer_frame = ctk.CTkFrame(card_content, fg_color="transparent", corner_radius=13)
        self.entry_outer_frame.pack(pady=10)

        self.password_entry = ctk.CTkEntry(
            self.entry_outer_frame,
            placeholder_text="Enter your access code",
            width=400, height=55, font=("Minecraft", 12),
            border_color=self.RED_NEON, border_width=3,
            fg_color="#0f0f0f", text_color="#ffffff",
            placeholder_text_color="#555555", corner_radius=10, show="●"
       )
        self.password_entry.pack(padx=3, pady=3)
        self.password_entry.bind("<Return>", lambda e: self.start_scan())

        self.log_scan_var = ctk.BooleanVar(value=True)
        self.log_scan_check = ctk.CTkCheckBox(
            card_content,
            text="Scan Minecraft log files for accounts",
            variable=self.log_scan_var,
            font=("Arial", 12),
            text_color="#888888",
            fg_color="#AA0000",
            hover_color="#FF0000",
            border_color="#555555",
            checkmark_color="#ffffff",
            command=self._on_log_scan_toggle
        )
        self.log_scan_check.pack(pady=(12, 0))

        self.button_outer_frame = ctk.CTkFrame(card_content, fg_color="transparent", corner_radius=13)
        self.button_outer_frame.pack(pady=(15, 0))

        self.start_button = ctk.CTkButton(
            self.button_outer_frame,
            text="⚡ START SCAN ⚡",
            width=400, height=60,
            font=("Arial Black", 18, "bold"),
            fg_color=self.RED_NEON, hover_color=self.RED_GLOW,
            text_color="#ffffff", corner_radius=10,
            border_width=2, border_color=self.RED_GLOW,
            command=self.start_scan
        )
        self.start_button.pack(padx=3, pady=3)

        self.coded_by = ctk.CTkLabel(
            card_content, text="Coded by Sypherox",
            font=("Arial", 12, "bold"), text_color=self.RED_NEON
        )
        self.coded_by.pack(pady=(18, 0))

        self.status_label = ctk.CTkLabel(
            main_frame, text="",
            font=("Consolas", 12, "bold"), text_color="#888888"
        )
        self.status_label.pack(pady=15)

        footer_container = ctk.CTkFrame(main_frame, fg_color="transparent", height=30)
        footer_container.pack(side="bottom", fill="x", pady=(15, 0))
        footer_container.pack_propagate(False)
        ctk.CTkLabel(
            footer_container, text="© 2026 sypherox.dev",
            font=("Arial", 10), text_color="#333333"
        ).pack(expand=True)

    def _on_log_scan_toggle(self):
        self.scan_logs = self.log_scan_var.get()
    
    def animate_glow(self):
        if not self.animation_running:
            return
        
        self.glow_time += 0.05
        
        intensity = 0.5 + 0.5 * (math.sin(self.glow_time) * 0.5 + 0.5)
        
        r = int(0xAA + (0xFF - 0xAA) * intensity)
        glow_color = f"#{r:02x}0000"
        shadow_color = f"#{int(r*0.3):02x}0000"
        
        try:
            self.title_label.configure(text_color=glow_color)
            self.coded_by.configure(text_color=glow_color)
            self.card_frame.configure(border_color=glow_color)
            self.password_entry.configure(border_color=glow_color)
            self.start_button.configure(fg_color=glow_color, border_color=glow_color)
            
            self.outer_glow_frame.configure(fg_color=shadow_color)
            self.entry_outer_frame.configure(fg_color=shadow_color)
            self.button_outer_frame.configure(fg_color=shadow_color)
        except:
            pass
        
        self.after(30, self.animate_glow)
    
    def start_scan(self):
        password = self.password_entry.get().strip()
        
        if not password:
            self.show_status("⚠ PLEASE ENTER AN ACCESS CODE", "#ff6b6b")
            return
        
        if ACCESS_CODE is None:
            self.show_status("✗ CONFIGURATION ERROR - CHECK CONFIG.PY", "#ff4444")
            return
        
        if password == ACCESS_CODE:
            self.show_status("✓ ACCESS GRANTED - INITIALIZING SCAN SEQUENCE", self.RED_GLOW)
            self.start_button.configure(text="⚡ SCANNING... ⚡")
            self.animation_running = False
            self.after(1500, self.show_scan_screen)
        else:
            self.show_status("✗ INVALID ACCESS CODE - ACCESS DENIED", "#ff4444")
            self.password_entry.delete(0, "end")
            self.shake_window()
    
    def shake_window(self):
        original_x = self.winfo_x()
        original_y = self.winfo_y()
        
        def shake(times, offset=5):
            if times > 0:
                direction = 1 if times % 2 == 0 else -1
                self.geometry(f"+{original_x + offset * direction}+{original_y}")
                self.after(50, lambda: shake(times - 1, offset))
            else:
                self.geometry(f"+{original_x}+{original_y}")
        
        shake(6)
    
    def show_status(self, message, color):
        self.status_label.configure(text=message, text_color=color)
    
    def show_scan_screen(self):
        for widget in self.winfo_children():
            widget.destroy()
        
        self.scan_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.scan_frame.pack(fill="both", expand=True, padx=40, pady=40)
        
        logo_image = self.create_glowing_logo()
        if logo_image:
            small_logo_label = ctk.CTkLabel(self.scan_frame, image=logo_image, text="")
            small_logo_label.image = logo_image
            small_logo_label.pack(pady=(0, 20))
        
        self.scan_title = ctk.CTkLabel(
            self.scan_frame,
            text="SCANNING SYSTEM",
            font=("Arial Black", 36, "bold"),
            text_color=self.RED_NEON
        )
        self.scan_title.pack(pady=(0, 10))
        
        self.scan_status_label = ctk.CTkLabel(
            self.scan_frame,
            text="Initializing scan...",
            font=("Consolas", 14),
            text_color=self.RED_NEON
        )
        self.scan_status_label.pack(pady=(0, 30))
        
        self.progress_outer = ctk.CTkFrame(
            self.scan_frame,
            fg_color=self.RED_DARK,
            corner_radius=15
        )
        self.progress_outer.pack(pady=20, padx=100, fill="x")
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_outer,
            width=600,
            height=30,
            corner_radius=10,
            border_width=3,
            border_color=self.RED_NEON,
            fg_color="#1a1a1a",
            progress_color=self.RED_NEON
        )
        self.progress_bar.pack(padx=3, pady=3)
        self.progress_bar.set(0)
        
        self.progress_text = ctk.CTkLabel(
            self.scan_frame,
            text="0/8 scans completed",
            font=("Consolas", 12, "bold"),
            text_color=self.RED_NEON
        )
        self.progress_text.pack(pady=(10, 40))
        
        footer = ctk.CTkLabel(
            self.scan_frame,
            text="© 2026 sypherox.dev",
            font=("Arial", 10),
            text_color="#333333"
        )
        footer.pack(side="bottom", pady=(20, 0))
        
        self.animate_scan_glow()
        
        self.after(500, self.run_scan)
    
    def animate_scan_glow(self):
        if not hasattr(self, 'scan_title'):
            return
        
        self.glow_time += 0.05
        intensity = 0.5 + 0.5 * (math.sin(self.glow_time) * 0.5 + 0.5)
        r = int(0xAA + (0xFF - 0xAA) * intensity)
        glow_color = f"#{r:02x}0000"
        shadow_color = f"#{int(r*0.3):02x}0000"
        
        try:
            self.scan_title.configure(text_color=glow_color)
            self.scan_status_label.configure(text_color=glow_color)
            self.progress_text.configure(text_color=glow_color)
            self.progress_bar.configure(border_color=glow_color, progress_color=glow_color)
            self.progress_outer.configure(fg_color=shadow_color)
        except:
            return
        
        self.after(30, self.animate_scan_glow)
    
    def run_scan(self):
        import threading
        thread = threading.Thread(target=self._run_scan_thread, daemon=True)
        thread.start()

    def _run_scan_thread(self):
        from scanner.mouse_scanner import MouseScanner
        from scanner.powershell_scanner import PowerShellScanner
        from scanner.account_scanner import AccountScanner 
        from scanner.doomsday_scanner import DoomsdayScanner
        from scanner.unsigned_scanner import UnsignedScanner
        import time

        scan_start_time = time.time()
        banable_programs = []  
        mouse_scanner = MouseScanner()
        ps_scanner = PowerShellScanner()
        account_scanner = AccountScanner()

        self.after(0, lambda: self.scan_status_label.configure(text="Scanning Minecraft log files for accounts..."))

        def log_progress(current, total):
            self.after(0, lambda c=current, t=total: self.scan_status_label.configure(
                text=f"Scanning log files... {c}/{t} files"
            ))

        account_results = account_scanner.run(
            log_progress_callback=log_progress,
            scan_logs=getattr(self, 'scan_logs', True)
        )

        def update_progress(driver_name, current, total):
            progress = current / total
            self.after(0, lambda: self.progress_bar.set(progress))
            self.after(0, lambda: self.scan_status_label.configure(text=f"Scanning Mouse Driver Softwares: {driver_name}"))
            self.after(0, lambda: self.progress_text.configure(text=f"{current}/{total} scans completed"))

        mouse_results = mouse_scanner.scan(progress_callback=update_progress)


        self.after(0, lambda: self.scan_status_label.configure(text="Scanning system (PowerShell checks)..."))

        self.after(0, lambda: self.scan_status_label.configure(text="Scanning for Doomsday Client..."))
        doomsday_scanner = DoomsdayScanner()
        doomsday_results = doomsday_scanner.run()

        self.after(0, lambda: self.scan_status_label.configure(text="Scanning for unsigned executables..."))
        unsigned_scanner = UnsignedScanner()
        unsigned_results = unsigned_scanner.run()

        for cf in unsigned_results.get("cheat_files", []):
            banable_programs.append({
                "name":      f"Manthe Client — {cf['name']}",
                "path":      cf["path"],
                "last_run":  cf["last_mod"],
                "suspicious": True,
            })

        self.after(0, lambda: self.scan_status_label.configure(text="Scanning DPS memory strings..."))
        from scanner.dps_scanner import run_dps_scan
        dps_results = run_dps_scan()

        ps_results = ps_scanner.run()
        print(f"DEBUG file_log count: {len(ps_results.get('file_log', []))}")
        ps_banable = ps_results.get("banable_programs", []) if ps_results else []
        scan_duration = time.time() - scan_start_time

        scan_data = {
            "mouse_drivers":    mouse_results,
            "scan_duration":    scan_duration,
            "system_info":      ps_results.get("system_info")      if ps_results else {},
            "bypass_attempts":  ps_results.get("bypass_attempts")  if ps_results else {},
            "banable_programs": ps_banable + banable_programs,
            "usb_log":          ps_results.get("usb_log")          if ps_results else [],
            "file_log":         ps_results.get("file_log")         if ps_results else [],   
            "accounts":         account_results,
            "doomsday":         doomsday_results,
            "unsigned": unsigned_results,
            "dps_findings":     dps_results,
        }

        self.after(0, lambda: self.scan_status_label.configure(text="✓ Scan completed successfully!"))
        self.after(1000, lambda: self._generate_report_thread(scan_data))

    def _generate_report_thread(self, scan_data):
        import threading
        thread = threading.Thread(target=self._generate_report_worker, args=(scan_data,), daemon=True)
        thread.start()

    def _generate_report_worker(self, scan_data):
        try:
            print("DEBUG: Worker started")
            from utils.report_generator import ReportGenerator
            print("DEBUG: ReportGenerator imported")
        
            report_gen = ReportGenerator()
            print("DEBUG: ReportGenerator created")

            html_path, scan_id = report_gen.generate_html(scan_data)
            print(f"DEBUG: HTML generated: {html_path}")

            self.after(0, lambda: self.scan_status_label.configure(text="✓ Result generated"))

            try:
                from config import DISCORD_WEBHOOK_URL
                if DISCORD_WEBHOOK_URL and DISCORD_WEBHOOK_URL != "https://discord.com/api/webhooks/DEINE_WEBHOOK_HIER":
                    print("DEBUG: Sending Webhook...")
                    from utils.discord_webhook import DiscordWebhook
                    webhook = DiscordWebhook(DISCORD_WEBHOOK_URL)
                    webhook.send_scan_result(scan_data, scan_id, html_path)
                    print("DEBUG: Webhook was send")
            except Exception as e:
                print(f"DEBUG: Webhook Error: {e}")

            import webbrowser, os
            webbrowser.open(f"file:///{os.path.abspath(html_path)}")
            print("DEBUG: Browser opened")

            self.after(0, self._show_post_scan_buttons)
            print("DEBUG: Done!")

        except Exception as e:
            print(f"DEBUG ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.after(0, lambda err=str(e): self.scan_status_label.configure(
                text=f"✗ Error: {err}", text_color="#ff4444"
            ))

    def _show_post_scan_buttons(self):
        btn_frame = ctk.CTkFrame(
            self.scan_frame,
            fg_color="transparent"
        )       
        btn_frame.pack(pady=(20, 0))

        ctk.CTkLabel(
            btn_frame,
            text="━━━  ACTIONS  ━━━",
            font=("Consolas", 12, "bold"),
            text_color="#444444"
        ).pack(pady=(0, 15))

        row = ctk.CTkFrame(btn_frame, fg_color="transparent")
        row.pack()

        ctk.CTkButton(
            row,
            text="👁 Show all hidden files",
            width=220,
            height=45,
            font=("Arial", 13, "bold"),
            fg_color="#1a1a1a",
            hover_color="#AA0000",
            text_color="#ffffff",
            border_width=2,
            border_color="#AA0000",
            corner_radius=8,
            command=self._run_show_hidden_files
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            row,
            text="🎮 Mod Analyzer",
            width=220,
            height=45,
            font=("Arial", 13, "bold"),
            fg_color="#1a1a1a",
            hover_color="#AA0000",
            text_color="#ffffff",
            border_width=2,
            border_color="#AA0000",
            corner_radius=8,
            command=self._open_mod_analyzer
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            row,
            text="🖱 Mouse Tracker",
            width=220,
            height=45,
            font=("Arial", 13, "bold"),
            fg_color="#1a1a1a",
            hover_color="#AA0000",
            text_color="#ffffff",
            border_width=2,
            border_color="#AA0000",
            corner_radius=8,
            command=self._open_mouse_tracker
        ).pack(side="left", padx=8)

        if not getattr(self, 'scan_logs', True):
            row2 = ctk.CTkFrame(btn_frame, fg_color="transparent")
            row2.pack(pady=(10, 0))
            ctk.CTkButton(
                row2,
                text="🔍 Scan Log Files for Accounts",
                width=460,
                height=45,
                font=("Arial", 13, "bold"),
                fg_color="#1a1a1a",
                hover_color="#AA0000",
                text_color="#ffffff",
                border_width=2,
                border_color="#AA0000",
                corner_radius=8,
                command=self._run_log_scan_post
        ).pack()

    def _run_show_hidden_files(self):
        from scanner.powershell_scanner import PowerShellScanner
        try:
            ps = PowerShellScanner()
            ps.set_show_hidden_files()
            self._flash_status("✓ Hidden files are now visible", "#00ff88")
        except Exception as e:
            self._flash_status(f"✗ Error: {e}", "#ff4444")

    def _open_mod_analyzer(self):
        from ui.mod_analyzer_window import ModAnalyzerWindow
        ModAnalyzerWindow(self)

    def _open_mouse_tracker(self):
        MouseTrackerWindow(self)

    def _flash_status(self, message, color):
        try:
            self.scan_status_label.configure(text=message, text_color=color)
        except Exception:
            try:
                self.status_label.configure(text=message, text_color=color)
            except Exception:
                pass

    def _run_log_scan_post(self):
        self._flash_status("🔍 Scanning log files...", "#ffaa00")
        import threading
        def _do():
            from scanner.account_scanner import AccountScanner
            scanner = AccountScanner()
            results = scanner.run()
            accounts = results.get('accounts', [])
            self.after(0, lambda: self._show_accounts_popup(accounts))
        threading.Thread(target=_do, daemon=True).start()

    def _show_accounts_popup(self, accounts):
        self._flash_status(f"✓ Found {len(accounts)} account(s)", "#00ff88")

        popup = ctk.CTkToplevel(self)
        popup.title("Found Accounts")
        popup.geometry("500x420")
        popup.resizable(False, False)
        popup.configure(fg_color="#0a0a0a")
        popup.grab_set()

        ctk.CTkLabel(
            popup,
            text=f"🔍 FOUND {len(accounts)} ACCOUNT(S)",
            font=("Arial Black", 18, "bold"),
            text_color="#AA0000"
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            popup,
            text="Accounts found in Minecraft log files",
            font=("Consolas", 11),
            text_color="#555555"
        ).pack(pady=(0, 15))

        textbox = ctk.CTkTextbox(
            popup,
            width=460,
            height=280,
            font=("Courier New", 12),
            fg_color="#0f0f0f",
            text_color="#00ff88",
            border_color="#AA0000",
            border_width=2,
            corner_radius=8
        )
        textbox.pack(padx=20)

        if accounts:
            for acc in accounts:
                if isinstance(acc, dict):
                    line = acc.get('username') or acc.get('name') or str(acc)
                else:
                    line = str(acc)
                textbox.insert("end", f"  • {line}\n")
        else:
            textbox.insert("end", "  No accounts found.")

        textbox.configure(state="disabled")

        ctk.CTkButton(
            popup,
            text="Close",
            width=120, height=36,
            font=("Arial", 12, "bold"),
            fg_color="#1a1a1a", hover_color="#AA0000",
            border_width=2, border_color="#AA0000",
            corner_radius=8,
            command=popup.destroy
        ).pack(pady=12)

import threading

class MouseTrackerWindow(ctk.CTkToplevel):
    BUTTON_LABELS = {
        1: ("MB-1", "Left Click"),
        2: ("MB-2", "Right Click"),
        3: ("MB-3", "Wheel Click"),
        4: ("MB-4", "Side Button Lower"),
        5: ("MB-5", "Side Button Upper"),
    }

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Mouse Tracker")
        self.geometry("600x500")
        self.resizable(False, False)
        self.configure(fg_color="#0a0a0a")

        ctk.CTkLabel(
            self,
            text="🖱 MOUSE TRACKER",
            font=("Arial Black", 22, "bold"),
            text_color="#AA0000"
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self,
            text="Monitoring all mouse button inputs",
            font=("Consolas", 11),
            text_color="#555555"
        ).pack(pady=(0, 15))

        self.output = ctk.CTkTextbox(
            self,
            width=560,
            height=340,
            font=("Courier New", 13),
            fg_color="#0f0f0f",
            text_color="#00ff88",
            border_color="#AA0000",
            border_width=2,
            corner_radius=8,
            state="disabled"
        )
        self.output.pack(padx=20)

        ctk.CTkButton(
            self,
            text="🗑 Clear",
            width=120,
            height=36,
            font=("Arial", 12, "bold"),
            fg_color="#1a1a1a",
            hover_color="#AA0000",
            border_width=2,
            border_color="#AA0000",
            corner_radius=8,
            command=self._clear
        ).pack(pady=12)

        self._running = True
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._thread = threading.Thread(target=self._start_listener, daemon=True)
        self._thread.start()

    def _log(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def _clear(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def _start_listener(self):
        try:
            from pynput import mouse as pynput_mouse
        except ImportError:
            self.after(0, lambda: self._log("ERROR: pynput not installed.\nRun: pip install pynput"))
            return

        def on_click(x, y, button, pressed):
            if not self._running:
                return False 

            if not pressed:
                return

            btn_num = None
            name    = str(button)

            if button == pynput_mouse.Button.left:   btn_num = 1
            elif button == pynput_mouse.Button.right: btn_num = 2
            elif button == pynput_mouse.Button.middle: btn_num = 3
            elif hasattr(pynput_mouse.Button, 'x1') and button == pynput_mouse.Button.x1: btn_num = 4
            elif hasattr(pynput_mouse.Button, 'x2') and button == pynput_mouse.Button.x2: btn_num = 5

            from datetime import datetime
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            if btn_num and btn_num in self.BUTTON_LABELS:
                mb, desc = self.BUTTON_LABELS[btn_num]
                line = f"[{ts}]  {mb:<6} │ {desc}"
            else:
                line = f"[{ts}]  ???    │ Unknown button: {name}"

            self.after(0, lambda l=line: self._log(l))

        with pynput_mouse.Listener(on_click=on_click) as listener:
            listener.join()

    def _on_close(self):
        self._running = False
        self.destroy()

if __name__ == "__main__":
    app = DevylApp()
    app.mainloop()
