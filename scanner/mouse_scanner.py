import os
import glob
from datetime import datetime
from pathlib import Path

class MouseScanner:
    def __init__(self):
        self.results = []
        self.username = os.getenv('USERNAME')
    
    def scan(self, progress_callback=None):
        self.results = []
        
        scanners = [
            ("SteelSeries", self.scan_steelseries),
            ("Roccat", self.scan_roccat),
            ("Razer Synapse", self.scan_razer),
            ("Logitech G HUB", self.scan_lghub),
            ("Lamzu", self.scan_lamzu),
            ("Glorious", self.scan_glorious),
            ("Corsair", self.scan_corsair),
            ("Cooler Master", self.scan_coolermaster),
        ]
        
        total = len(scanners)
        for idx, (name, scanner_func) in enumerate(scanners):
            if progress_callback:
                progress_callback(name, idx + 1, total)
            
            result = scanner_func()
            if result:
                self.results.append(result)
        
        return self.results
    
    def scan_steelseries(self):
        paths = [
            rf"C:\Users\{self.username}\AppData\Roaming\steelseries-engine-3-client",
            rf"C:\Users\{self.username}\AppData\Roaming\steelseries-gg-client"
        ]
        
        for base_path in paths:
            if os.path.exists(base_path):
                log_files = glob.glob(os.path.join(base_path, "*.log"))
                if log_files:
                    latest_log = max(log_files, key=os.path.getmtime)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(latest_log))
                    
                    return {
                        "driver": "SteelSeries Engine",
                        "path": base_path,
                        "file": os.path.basename(latest_log),
                        "last_modified": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "suspicious": self._is_recent_modification(mod_time),
                        "details": f"Latest log file: {os.path.basename(latest_log)}"
                    }
        return None
    
    def scan_roccat(self):
        path = rf"C:\Users\{self.username}\AppData\Roaming\Roccat\Log"
        
        if os.path.exists(path):
            files = glob.glob(os.path.join(path, "*.*"))
            if files:
                latest_file = max(files, key=os.path.getmtime)
                mod_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
                
                return {
                    "driver": "Roccat",
                    "path": path,
                    "file": os.path.basename(latest_file),
                    "last_modified": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "suspicious": self._is_recent_modification(mod_time),
                    "details": f"Latest file: {os.path.basename(latest_file)}"
                }
        return None
    
    def scan_razer(self):
        path = r"C:\ProgramData\Razer\Synapse3\Log"
        log_file = os.path.join(path, "SynapseService.log")
        
        if os.path.exists(log_file):
            mod_time = datetime.fromtimestamp(os.path.getmtime(log_file))
            
            macro_detections = []
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    for line in lines:
                        if "Successfully executed macro-delete command" in line:
                            macro_detections.append(("Macro Deleted", line.strip()))
                        elif "Successfully executed macro-set command" in line:
                            macro_detections.append(("Macro Set", line.strip()))
                        elif "Successfully executed deletebyfeature command" in line:
                            macro_detections.append(("Delete by Feature", line.strip()))
            except Exception as e:
                macro_detections = [("Error", f"Could not read log: {str(e)}")]
            
            details = f"SynapseService.log"
            if macro_detections:
                details += f"\n⚠️ MACRO ACTIVITY DETECTED ({len(macro_detections)} entries)"
            
            is_suspicious = self._is_recent_modification(mod_time, hours=2) or len(macro_detections) > 0
            
            return {
                "driver": "Razer Synapse",
                "path": path,
                "file": "SynapseService.log",
                "last_modified": mod_time.strftime("%d.%m.%Y %H:%M:%S"),
                "suspicious": is_suspicious,
                "details": details,
                "macro_detections": macro_detections
            }
        return None
    
    def scan_lghub(self):
        path = rf"C:\Users\{self.username}\AppData\Local\LGHUB"
        settings_db = os.path.join(path, "settings.db")
        
        if os.path.exists(settings_db):
            mod_time = datetime.fromtimestamp(os.path.getmtime(settings_db))
            
            return {
                "driver": "Logitech G HUB",
                "path": path,
                "file": "settings.db",
                "last_modified": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                "suspicious": self._is_recent_modification(mod_time),
                "details": "settings.db database file"
            }
        return None
    
    def scan_lamzu(self):
        paths = [
            rf"C:\Users\{self.username}\AppData\Local\LAMZU\LAMZU\LOG",
            rf"C:\Users\{self.username}\AppData\Local\LAMZU\LOG"
        ]
        
        for path in paths:
            if os.path.exists(path):
                files = glob.glob(os.path.join(path, "*.*"))
                if files:
                    latest_file = max(files, key=os.path.getmtime)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
                    
                    return {
                        "driver": "Lamzu",
                        "path": path,
                        "file": os.path.basename(latest_file),
                        "last_modified": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "suspicious": self._is_recent_modification(mod_time),
                        "details": f"Latest log: {os.path.basename(latest_file)}"
                    }
        return None
    
    def scan_glorious(self):
        path = rf"C:\Users\{self.username}\AppData\Roaming\Glorious Core\logs"
        
        if os.path.exists(path):
            files = glob.glob(os.path.join(path, "*.*"))
            if files:
                latest_file = max(files, key=os.path.getmtime)
                mod_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
                
                return {
                    "driver": "Glorious Core",
                    "path": path,
                    "file": os.path.basename(latest_file),
                    "last_modified": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "suspicious": self._is_recent_modification(mod_time),
                    "details": f"Latest log: {os.path.basename(latest_file)}"
                }
        return None
    
    def scan_corsair(self):
        path = rf"C:\Users\{self.username}\AppData\Roaming\CUE"
        
        if os.path.exists(path):
            config_files = glob.glob(os.path.join(path, "*.config")) + glob.glob(os.path.join(path, "*.cfg"))
            if config_files:
                latest_file = max(config_files, key=os.path.getmtime)
                mod_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
                
                return {
                    "driver": "Corsair iCUE",
                    "path": path,
                    "file": os.path.basename(latest_file),
                    "last_modified": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "suspicious": self._is_recent_modification(mod_time),
                    "details": f"Config file: {os.path.basename(latest_file)}"
                }
        return None
    
    def scan_coolermaster(self):
        paths = [
            rf"C:\ProgramData\CoolerMaster\MASTERPLUS",
            rf"C:\ProgramData\CoolerMaster\MASTERPLUS\Log"
        ]
        
        for path in paths:
            if os.path.exists(path):
                files = glob.glob(os.path.join(path, "*.log")) + glob.glob(os.path.join(path, "*.*"))
                if files:
                    latest_file = max(files, key=os.path.getmtime)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
                    
                    return {
                        "driver": "Cooler Master",
                        "path": path,
                        "file": os.path.basename(latest_file),
                        "last_modified": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "suspicious": self._is_recent_modification(mod_time),
                        "details": f"Latest file: {os.path.basename(latest_file)}"
                    }
        return None
    
    def _is_recent_modification(self, mod_time, hours=2):
        from datetime import datetime, timedelta
        now = datetime.now()
        diff = now - mod_time
        return diff.total_seconds() <= (hours * 3600)