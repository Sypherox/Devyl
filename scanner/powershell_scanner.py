import subprocess
import json
from datetime import datetime, timedelta


class PowerShellScanner:
    def __init__(self):
        pass

    def set_show_hidden_files(self):
        import tempfile
        import os

        script = '\n'.join([
            'Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" -Name "Hidden" -Value 1 -ErrorAction SilentlyContinue',
            'Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" -Name "ShowSuperHidden" -Value 1 -ErrorAction SilentlyContinue',
            'Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue',
            'Start-Sleep -Milliseconds 500',
        ])

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8') as f:
            f.write(script)
            tmp = f.name

        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", tmp],
                capture_output=True
            )
        finally:
            os.unlink(tmp)

    def run(self):
        import tempfile, os

        results = {}

        scripts = {
            "system":  self._build_system_script(),
            "bypass":  self._build_bypass_script(),
            "filelog": self._build_filelog_script(),
        }

        for key, script in scripts.items(): 
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8') as f:
                f.write(script)
                temp_path = f.name

            try:
                completed = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", temp_path],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=60 if key == "filelog" else 25
                )
            except subprocess.TimeoutExpired:
                print(f"Timeout on script: {key}")
                results[key] = {}
                continue
            finally:
                os.unlink(temp_path)

            try:
                results[key] = json.loads(completed.stdout.strip())
            except Exception as e:
                print(f"JSON parse error ({key}): {e}")
                results[key] = {}

        merged = {
            "SystemInfo":      results.get("system", {}).get("SystemInfo", {}),
            "BypassAttempts":  results.get("bypass", {}).get("BypassAttempts", {}),
            "BanablePrograms": results.get("bypass", {}).get("BanablePrograms", []),
            "UsbLog":          results.get("bypass", {}).get("UsbLog", []),
            "FileLog":         results.get("filelog", {}).get("FileLog", []),
        }

        print("=== PS_RESULTS DEBUG ===")
        print(merged)
        print("========================")

        return self._post_process(merged)

    def _build_system_script(self) -> str:
        lines = [
            '$ErrorActionPreference = "SilentlyContinue"',
            '',
            '$os = Get-CimInstance Win32_OperatingSystem',
            '$lastBoot = $os.LastBootUpTime',
            '$now = Get-Date',
            '$uptimeSpan = $now - $lastBoot',
            '',
            'if ($uptimeSpan.TotalDays -ge 1) {',
            '    $uptimeString = "{0}d {1}h {2}m" -f [int]$uptimeSpan.TotalDays, $uptimeSpan.Hours, $uptimeSpan.Minutes',
            '} elseif ($uptimeSpan.TotalHours -ge 1) {',
            '    $uptimeString = "{0}h {1}m" -f [int]$uptimeSpan.TotalHours, $uptimeSpan.Minutes',
            '} else {',
            '    $uptimeString = "{0}m" -f [int]$uptimeSpan.TotalMinutes',
            '}',
            '',
            '$drives = Get-CimInstance -ClassName Win32_LogicalDisk | Where-Object { $_.DriveType -ne 5 }',
            '$connectedDrivers = @()',
            'if ($drives) {',
            '    foreach ($drive in $drives) {',
            '        $connectedDrivers += ("{0}: {1}" -f $drive.DeviceID, $drive.FileSystem)',
            '    }',
            '}',
            '',
            '$serviceNames = @("SysMain","PcaSvc","DPS","EventLog","Bam")',
            '$servicesResult = @{}',
            'foreach ($name in $serviceNames) {',
            '    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue',
            '    if ($null -ne $svc) {',
            '        $status = "Unknown"; $timeInfo = ""; $stateInfo = ""',
            '        if ($svc.Status -eq "Running") {',
            '            $status = "Running"',
            '            try {',
            '                $wmiProc = Get-WmiObject Win32_Service -Filter "Name=\'$name\'" -ErrorAction SilentlyContinue',
            '                if ($wmiProc -and $wmiProc.ProcessId -gt 0) {',
            '                    $proc = Get-Process -Id $wmiProc.ProcessId -ErrorAction SilentlyContinue',
            '                    if ($proc) { $timeInfo = $proc.StartTime.ToString("dd.MM.yyyy HH:mm:ss") }',
            '                }',
            '            } catch {}',
            '        } else {',
            '            $status = "Stopped"',
            '            $wmi = Get-WmiObject -Class Win32_Service -Filter "Name=\'$name\'" -ErrorAction SilentlyContinue',
            '            if ($wmi -and $wmi.StartMode -eq "Disabled") { $stateInfo = "Service manually disabled" }',
            '            else { $stateInfo = "Service manually stopped" }',
            '        }',
            '        $servicesResult[$name] = @{ Name = $name; Status = $status; TimeInfo = $timeInfo; StateInfo = $stateInfo }',
            '    }',
            '}',
            '',
            '$cmdLoggingEnabled = $true; $psLoggingEnabled = $true; $prefetchEnabled = $true',
            'try { $r = Get-ItemProperty "HKCU:\\Software\\Policies\\Microsoft\\Windows\\System" -Name "DisableCMD" -EA SilentlyContinue; if ($r -and $r.DisableCMD -eq 1) { $cmdLoggingEnabled = $false } } catch {}',
            'try { $r = Get-ItemProperty "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\PowerShell\\ScriptBlockLogging" -Name "EnableScriptBlockLogging" -EA SilentlyContinue; if ($r -and $r.EnableScriptBlockLogging -eq 0) { $psLoggingEnabled = $false } } catch {}',
            'try { $r = Get-ItemProperty "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters" -Name "EnablePrefetcher" -EA SilentlyContinue; if (-not $r -or $r.EnablePrefetcher -eq 0) { $prefetchEnabled = $false } } catch {}',
            '',
            '$noRecentDocs = $false',
            'try { $r = Get-ItemProperty "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer" -Name "NoRecentDocsHistory" -EA SilentlyContinue; if ($r -and $r.NoRecentDocsHistory -eq 1) { $noRecentDocs = $true } } catch {}',
            '',
            '$uavDisabled = $false; $uavReason = ""',
            'try {',
            '    $uaPath = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\UserAssist"',
            '    $uaSubkeys = Get-ChildItem $uaPath -EA SilentlyContinue',
            '    $hasCount = $false',
            '    foreach ($sk in $uaSubkeys) { $children = Get-ChildItem $sk.PSPath -EA SilentlyContinue; if ($children | Where-Object { $_.PSChildName -eq "Count" }) { $hasCount = $true } }',
            '    if (-not $hasCount) { $uavDisabled = $true; $uavReason = "No Count subkeys found" }',
            '    $noLog = Get-ItemProperty -Path $uaPath -Name "NoLog" -EA SilentlyContinue',
            '    if ($noLog -and $noLog.NoLog -eq 1) { $uavDisabled = $true; $uavReason = "NoLog=1 set" }',
            '} catch {}',
            '',
            '$result = @{',
            '    SystemInfo = @{',
            '        LastBoot = $lastBoot.ToString("dd.MM.yyyy HH:mm:ss")',
            '        Uptime = $uptimeString',
            '        ConnectedDrivers = $connectedDrivers',
            '        Services = $servicesResult',
            '        CmdLoggingEnabled = $cmdLoggingEnabled',
            '        PsLoggingEnabled = $psLoggingEnabled',
            '        PrefetchEnabled = $prefetchEnabled',
            '        NoRecentDocs = $noRecentDocs',
            '        UavDisabled = $uavDisabled',
            '        UavReason = $uavReason',
            '    }',
            '}',
            '$result | ConvertTo-Json -Depth 6',
       ]
        return '\n'.join(lines)


    def _build_bypass_script(self) -> str:
        lines = [
            '$ErrorActionPreference = "SilentlyContinue"',
            '', 
            '$usnClearedTime = $null',
            'try { $ev = Get-WinEvent -LogName "Application" -FilterXPath "*[System[EventID=3079]]" -MaxEvents 1 -EA SilentlyContinue; if ($ev) { $usnClearedTime = $ev.TimeCreated.ToString("dd.MM.yyyy HH:mm:ss") } } catch {}',
            '',
            '$eventClearedTime = $null',
            'try { $ev = Get-WinEvent -LogName "System" -FilterXPath "*[System[EventID=104 or EventID=1102]]" -MaxEvents 1 -EA SilentlyContinue; if ($ev) { $eventClearedTime = $ev.TimeCreated.ToString("dd.MM.yyyy HH:mm:ss") } } catch {}',
            '',
            '$securityLogCleared = $null',
            'try { $ev = Get-WinEvent -LogName "Security" -FilterXPath "*[System[EventID=1102]]" -MaxEvents 1 -EA SilentlyContinue; if ($ev) { $securityLogCleared = $ev.TimeCreated.ToString("dd.MM.yyyy HH:mm:ss") } } catch {}', 
            '',
            '$lastShutdown = $null',
            'try { $ev = Get-WinEvent -LogName "System" -FilterXPath "*[System[EventID=1074]]" -MaxEvents 1 -EA SilentlyContinue; if ($ev) { $lastShutdown = $ev.TimeCreated.ToString("dd.MM.yyyy HH:mm:ss") } } catch {}',
            '',
            '$timeChanged = $null',
            'try { $ev = Get-WinEvent -LogName "Security" -FilterXPath "*[System[EventID=4616]]" -MaxEvents 1 -EA SilentlyContinue; if ($ev) { $timeChanged = $ev.TimeCreated.ToString("dd.MM.yyyy HH:mm:ss") } } catch {}',
            '',
            '$eventLogSvcEvt = $null',
            'try { $ev = Get-WinEvent -LogName "System" -FilterXPath "*[System[EventID=6005]]" -MaxEvents 1 -EA SilentlyContinue; if ($ev) { $eventLogSvcEvt = @{ Time = $ev.TimeCreated.ToString("dd.MM.yyyy HH:mm:ss"); Id = $ev.Id; Info = $ev.Message } } } catch {}',
            '',
            '$deviceConfig = $null',
            'try { $ev = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -FilterXPath "*[System[EventID=400]]" -MaxEvents 1 -EA SilentlyContinue; if ($ev) { $deviceConfig = @{ Time = $ev.TimeCreated.ToString("dd.MM.yyyy HH:mm:ss"); Id = $ev.Id; Info = $ev.Message } } } catch {}',
            '',
            '$prefetchPath = "$env:SystemRoot\\Prefetch"',
            '$hiddenFileNames = @(); $roFileNames = @(); $duplicates = @()',
            'if (Test-Path $prefetchPath) {',
            '    $hf = Get-ChildItem $prefetchPath -Hidden -EA SilentlyContinue; if ($hf) { $hiddenFileNames = @($hf | Select-Object -ExpandProperty Name) }',
            '    $rf = Get-ChildItem $prefetchPath -EA SilentlyContinue | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReadOnly }; if ($rf) { $roFileNames = @($rf | Select-Object -ExpandProperty Name) }',
            '    $grouped = Get-ChildItem $prefetchPath -EA SilentlyContinue | Group-Object Name',
            '    foreach ($g in $grouped) { if ($g.Count -gt 1) { $duplicates += $g.Group.Name } }',
            '}',
            '',
            '$recycleInfo = $null',
            'try {',
            '    $rbPath = "$env:SystemDrive\\`$Recycle.Bin"',
            '    if (Test-Path $rbPath) {',
            '        $rbFolder = Get-Item -LiteralPath $rbPath -Force',     
            '        $latestMod = $rbFolder.LastWriteTime; $latestName = $null',
            '        $userFolders = Get-ChildItem -LiteralPath $rbPath -Directory -Force -EA SilentlyContinue',
            '        if ($userFolders) {',
            '            foreach ($uf in $userFolders) {',
            '                if ($uf.LastWriteTime -gt $latestMod) { $latestMod = $uf.LastWriteTime }',
            '                $uItems = Get-ChildItem -LiteralPath $uf.FullName -File -Force -EA SilentlyContinue',
            '                if ($uItems) { $lf = $uItems | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if ($lf -and $lf.LastWriteTime -gt $latestMod) { $latestMod = $lf.LastWriteTime; $latestName = $lf.Name } }',
            '            }',
            '        }',
            '        $recycleInfo = @{ LastModified = $latestMod.ToString("dd.MM.yyyy HH:mm:ss"); LastItem = $latestName }',
            '    }',
            '} catch {}',
            '',
            '$historyPath = "$env:USERPROFILE\\AppData\\Roaming\\Microsoft\\Windows\\PowerShell\\PSReadline\\ConsoleHost_history.txt"',
            '$historyInfo = $null',
            'if (Test-Path $historyPath) { $fi = Get-Item $historyPath; $historyInfo = @{ Path = $historyPath; LastWrite = $fi.LastWriteTime.ToString("dd.MM.yyyy HH:mm:ss"); Attributes = $fi.Attributes.ToString(); LengthBytes = $fi.Length } }',
            '',
            '$banablePrograms = @()',
            '$programNames = @("VeraCrypt","h2testw","DefenderControl","SetFileDate","BulkFileChanger","iObitLocker","PowerShell_ISE")',
            '$cutoff12h = (Get-Date).AddHours(-12)',
            'foreach ($prog in $programNames) {',
            '    $found = $false; $lastRun = $null; $foundPath = $null',
            '    $pfFiles = Get-ChildItem "$env:SystemRoot\\Prefetch" -EA SilentlyContinue | Where-Object { $_.Name -like "$prog*" }',
            '    if ($pfFiles) { $found = $true; $latest = $pfFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1; $lastRun = $latest.LastWriteTime.ToString("dd.MM.yyyy HH:mm:ss"); $foundPath = $latest.FullName }',
            '    if ($found) {',
            '        $suspicious = $false',
            '        if ($lastRun) { $dt = [datetime]::ParseExact($lastRun, "dd.MM.yyyy HH:mm:ss", $null); if ($dt -gt $cutoff12h) { $suspicious = $true } }',
            '        $banablePrograms += @{ Name = $prog; LastRun = $lastRun; Suspicious = $suspicious; Path = $foundPath }',
            '    }',
            '}',
            '',
            '$renamedExes = @()',
            'try {',
            '    $allDrives = Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 } | Select-Object -ExpandProperty DeviceID',
            '    foreach ($drv in $allDrives) {',
            '        $output = cmd /c "findstr /m /c:""!This program cannot be run in DOS mode."" ""$drv\\*"" 2>nul"',
            '        if ($output) { foreach ($file in $output) { $ext = [System.IO.Path]::GetExtension($file).ToLower(); if ($ext -ne ".exe" -and $ext -ne ".dll" -and $ext -ne "" -and $file -ne "") { $fi = Get-Item -LiteralPath $file -EA SilentlyContinue; if ($fi) { $renamedExes += @{ Path = $file; Extension = $ext; LastModified = $fi.LastWriteTime.ToString("dd.MM.yyyy HH:mm:ss") } } } } }',
            '    }',
            '} catch {}',
            '',
            '$usbLog = @()',
            'try { $usbEvents = Get-WinEvent -LogName "Microsoft-Windows-Kernel-PnP/Configuration" -EA SilentlyContinue | Where-Object { $_.Id -eq 410 } | Select-Object -First 100; foreach ($ev in $usbEvents) { $usbLog += @{ Time = $ev.TimeCreated.ToString("dd.MM.yyyy HH:mm:ss"); Message = ($ev.Message -split "`n")[0].Trim() } } } catch {}',
            '',
            '$result = @{',
            '    BypassAttempts = @{',
            '        UsnClearedTime = $usnClearedTime',
            '        EventLogsCleared = $eventClearedTime',
            '        SecurityLogCleared = $securityLogCleared',
            '        LastShutdown = $lastShutdown',
            '        TimeChanged = $timeChanged',
            '        EventLogServiceEvt = $eventLogSvcEvt',
            '        DeviceConfigEvt = $deviceConfig',  
            '        HiddenPrefetch = $hiddenFileNames',
            '        ReadOnlyPrefetch = $roFileNames',
            '        DuplicatePrefetch = $duplicates',
            '        RecycleBin = $recycleInfo',
            '        ConsoleHistory = $historyInfo',
            '        RenamedExes = $renamedExes',
            '    }',
            '    BanablePrograms = $banablePrograms',
            '    UsbLog = $usbLog',
            '}',
            '$result | ConvertTo-Json -Depth 6',
        ]
        return '\n'.join(lines)


    def _build_filelog_script(self) -> str:
        lines = [
            '$ErrorActionPreference = "SilentlyContinue"',
            '',
            '$fileLog = @()',
            'try {',
            '    $cutoffTime = (Get-Date).AddHours(-6)',
            '    $pfPath = "$env:SystemRoot\\Prefetch"',
            '    if (Test-Path $pfPath) {', 
            '        $pfFiles = Get-ChildItem $pfPath -Filter "*.pf" -EA SilentlyContinue | Where-Object { $_.LastWriteTime -ge $cutoffTime } | Sort-Object LastWriteTime -Descending',
            '        foreach ($pf in $pfFiles) { $exeName = $pf.Name -replace "-[A-F0-9]+\\.pf$", ""; $fileLog += @{ Time = $pf.LastWriteTime.ToString("dd.MM.yyyy HH:mm:ss"); File = $exeName; Reason = "Executed (Prefetch)" } }',
            '    }',
            '    $usnOutput = $null',
            '    try {',
            '        $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())',
            '        $isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)',
            '        if ($isAdmin) { $usnOutput = & fsutil usn readjournal C: csv 2>$null }',
            '    } catch {}',
            '    if ($usnOutput) {',
            '        $usnLines = $usnOutput | Select-Object -Skip 1',
            '        foreach ($line in $usnLines) {',
            '            $cols = $line -split ","',
            '            if ($cols.Count -ge 5) {',
            '                $reason = $cols[4].Trim().Trim(\'"\')',
            '                if ($reason -match "RENAME") {',
            '                    $timeRaw = $cols[1].Trim().Trim(\'"\')',
            '                    try { $dt = [datetime]::Parse($timeRaw); if ($dt -ge $cutoffTime) { $fileLog += @{ Time = $dt.ToString("dd.MM.yyyy HH:mm:ss"); File = $cols[2].Trim().Trim(\'"\'); Reason = "Renamed" } } } catch {}',
            '                }',
            '            }',
            '        }',
            '    }',
            '    $fileLog = @($fileLog | Sort-Object { $_["Time"] } -Descending)',
            '} catch {}',
            '',
            '$result = @{ FileLog = $fileLog }',
            '$result | ConvertTo-Json -Depth 4',
        ]
        return '\n'.join(lines)


    def _post_process(self, data: dict):
        now = datetime.now()

        sys_data = data.get("SystemInfo", {})
        bypass = data.get("BypassAttempts", {})

        services = sys_data.get("Services", {})
        service_results = []
        for name in ["SysMain", "PcaSvc", "DPS", "EventLog", "Bam"]:
            svc = services.get(name)
            if not svc:
                continue
            status = svc.get("Status")
            time_info = svc.get("TimeInfo") or "N/A"
            state_info = svc.get("StateInfo") or ""
            if status == "Running":
                level = "Clean"
                reason = f"Running since {time_info}"
            else:
                level = "Suspicious"
                reason = state_info or f"Stopped at {time_info}"

            service_results.append({
                "name": name,
                "status": status,
                "level": level,
                "time_info": time_info,
                "state_info": state_info,
                "reason": reason
            })

        system_info = {
            "last_boot": sys_data.get("LastBoot"),
            "uptime": sys_data.get("Uptime"),
            "connected_drivers": sys_data.get("ConnectedDrivers", []),
            "services": service_results,
            "cmd_logging": "Clean" if sys_data.get("CmdLoggingEnabled") else "Suspicious",
            "ps_logging": "Clean" if sys_data.get("PsLoggingEnabled") else "Suspicious",
            "prefetch": "Clean" if sys_data.get("PrefetchEnabled") else "Suspicious",
        }

        def parse_dt(dt_str):
            if not dt_str:
                return None
            try:
                return datetime.strptime(dt_str, "%d.%m.%Y %H:%M:%S")
            except Exception:
                return None

        usn_time = parse_dt(bypass.get("UsnClearedTime"))
        logs_time = parse_dt(bypass.get("EventLogsCleared"))
        recycle_info = bypass.get("RecycleBin") or {}

        def recent(dt, days):
            return dt and (now - dt) <= timedelta(days=days)

        bypass_info = {
            "usn": {
                "time": bypass.get("UsnClearedTime"),
                "level": "Suspicious" if recent(usn_time, 3) else "Clean",
            },
            "eventlogs": {
                "time": bypass.get("EventLogsCleared"),
                "level": "Suspicious" if recent(logs_time, 3) else "Clean",
            },
            "last_shutdown": bypass.get("LastShutdown"),
            "time_changed": bypass.get("TimeChanged"),
            "eventlog_service": bypass.get("EventLogServiceEvt"),
            "device_config": bypass.get("DeviceConfigEvt"),
            "hidden_prefetch": {
                "items": bypass.get("HiddenPrefetch") or [],
                "level": "Clean" if not bypass.get("HiddenPrefetch") else "Suspicious",
            },
            "readonly_prefetch": {
                "items": bypass.get("ReadOnlyPrefetch") or [],
                "level": "Clean" if not bypass.get("ReadOnlyPrefetch") else "Suspicious",
            },
            "duplicate_prefetch": {
                "items": bypass.get("DuplicatePrefetch") or [],
                "level": "Clean" if not bypass.get("DuplicatePrefetch") else "Suspicious",
            },
            "recycle_bin": {
                "last_modified": recycle_info.get("LastModified"),
                "last_item": recycle_info.get("LastItem"),
                "level": "Suspicious"
                if (parse_dt(recycle_info.get("LastModified"))
                    and (now - parse_dt(recycle_info.get("LastModified")) <= timedelta(hours=2)))
                else "Clean"
            },
            "console_history": bypass.get("ConsoleHistory"),
        }

        raw_banable = data.get("BanablePrograms") or []
        if isinstance(raw_banable, dict):
            raw_banable = list(raw_banable.values())
        banable_programs = []
        for p in raw_banable:
            banable_programs.append({
                "name":       p.get("Name", ""),
                "last_run":   p.get("LastRun"),
                "suspicious": bool(p.get("Suspicious", False)),
                "path":       p.get("Path"),
            })

        system_info["no_recent_docs"] = "Suspicious" if sys_data.get("NoRecentDocs") else "Clean"
        system_info["uav_disabled"]   = "Suspicious" if sys_data.get("UavDisabled")  else "Clean"
        system_info["uav_reason"]     = sys_data.get("UavReason") or ""

        sec_cleared_str = bypass.get("SecurityLogCleared")
        sec_cleared_dt  = parse_dt(sec_cleared_str)
        bypass_info["security_log_cleared"] = {
            "time":  sec_cleared_str,
            "level": "Suspicious" if recent(sec_cleared_dt, 1) else ("Info" if sec_cleared_str else "Clean"),
        }

        raw_renamed = bypass.get("RenamedExes") or []
        if isinstance(raw_renamed, dict):
           raw_renamed = list(raw_renamed.values())

        recent_renamed = []
        for item in raw_renamed:
            dt = parse_dt(item.get("LastModified"))
            if dt and (now - dt) <= timedelta(days=7):  
                recent_renamed.append(item)

        bypass_info["renamed_exes"] = {
            "items": recent_renamed,
            "level": "Suspicious" if recent_renamed else "Clean",
        }


        raw_usb = data.get("UsbLog") or []
        if isinstance(raw_usb, dict):
            raw_usb = list(raw_usb.values())

        cutoff_48h = now - timedelta(hours=48)
        usb_log = []
        for entry in raw_usb:
            try:
                entry_time = datetime.strptime(entry["Time"], "%d.%m.%Y %H:%M:%S")
                if entry_time >= cutoff_48h:
                    usb_log.append(entry)
            except:
                pass

        raw_file = data.get("FileLog") or []
        if isinstance(raw_file, dict):
            raw_file = list(raw_file.values())
        file_log = raw_file

        return {
            "system_info":     system_info,
            "bypass_attempts": bypass_info,
            "banable_programs": banable_programs,
            "usb_log":         usb_log,
            "file_log":        file_log,
        }
