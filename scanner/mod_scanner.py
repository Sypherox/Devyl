import subprocess
import json
import os
import tempfile


MOD_SCANNER_PS_SCRIPT = r"""
param([string]$ModsPath = "")

if (-not $ModsPath) {
    $ModsPath = "$env:USERPROFILE\AppData\Roaming\.minecraft\mods"
}

$result = @{
    ModsPath     = $ModsPath
    PathExists   = $false
    VerifiedMods = @()
    UnknownMods  = @()
    CheatMods    = @()
    MinecraftRunning = $false
    McStartTime  = ""
    McUptime     = ""
    Error        = ""
}

if (-not (Test-Path $ModsPath -PathType Container)) {
    $result.Error = "Mods folder not found: $ModsPath"
    $result | ConvertTo-Json -Depth 5
    exit
}

$result.PathExists = $true

$mcProc = Get-Process javaw -ErrorAction SilentlyContinue
if (-not $mcProc) { $mcProc = Get-Process java -ErrorAction SilentlyContinue }
if ($mcProc) {
    try {
        $start   = $mcProc.StartTime
        $elapsed = (Get-Date) - $start
        $result.MinecraftRunning = $true
        $result.McStartTime      = $start.ToString("dd.MM.yyyy HH:mm:ss")
        $result.McUptime         = "$($elapsed.Hours)h $($elapsed.Minutes)m $($elapsed.Seconds)s"
    } catch {}
}

$cheatStrings = @(
    "AimAssist", "KillAura", "AnchorTweaks", "AutoAnchor",
    "AutoCrystal", "AutoHitCrystal", "AutoDoubleHand",
    "AutoPot", "AutoTotem", "InventoryTotem", "LegitTotem",
    "AutoArmor", "ShieldBreaker", "TriggerBot", "AxeSpam",
    "FastPlace", "SelfDestruct", "WebMacro",

    "Velocity", "NoKnockback", "NoFall", "Sprint", "Blink",
    "Phase", "NoSlowdown", "SpeedHack",

    "HitboxExpand", "EntityHitbox", "HitboxMod", "ExpandedHitbox",
    "Hitboxes", "ReachExtend", "HitReach", "AttackRange", "ReachMod",

    "AutoClicker", "ClickAssist", "CpsBoost", "CpsMod",

    "PingSpoof", "JumpReset",

    "Scaffold", "FastBow", "ArrowSpam", "CriticalHit",
    "AntiFireball", "BowAimbot"
)

function Get-SHA1 {
    param([string]$filePath)
    return (Get-FileHash -Path $filePath -Algorithm SHA1).Hash
}

function Get-ZoneIdentifier {
    param([string]$filePath)
    $ads = Get-Content -Raw -Stream Zone.Identifier $filePath -ErrorAction SilentlyContinue
    if ($ads -match "HostUrl=(.+)") { return $matches[1].Trim() }
    return $null
}

function Fetch-Modrinth {
    param([string]$hash)
    try {
        $r = Invoke-RestMethod -Uri "https://api.modrinth.com/v2/version_file/$hash" `
             -Method Get -UseBasicParsing -ErrorAction Stop -TimeoutSec 5
        if ($r.project_id) {
            $p = Invoke-RestMethod -Uri "https://api.modrinth.com/v2/project/$($r.project_id)" `
                 -Method Get -UseBasicParsing -ErrorAction Stop -TimeoutSec 5
            return @{ Name = $p.title; Slug = $p.slug; Source = "Modrinth" }
        }
    } catch {}
    return @{ Name = ""; Slug = ""; Source = "" }
}

function Fetch-Megabase {
    param([string]$hash)
    try {
        $r = Invoke-RestMethod -Uri "https://megabase.vercel.app/api/query?hash=$hash" `
             -Method Get -UseBasicParsing -ErrorAction Stop -TimeoutSec 5
        if (-not $r.error -and $r.data.name) { return $r.data }
    } catch {}
    return $null
}

function Check-Strings {
    param([string]$filePath)
    $found = [System.Collections.Generic.List[string]]::new()
    try {
        $content = Get-Content -Raw $filePath -ErrorAction Stop
        foreach ($s in $cheatStrings) {
            if ($content -match [regex]::Escape($s)) { $found.Add($s) }
        }
    } catch {}
    return $found
}

$jarFiles = Get-ChildItem -Path $ModsPath -Filter *.jar -ErrorAction SilentlyContinue

foreach ($file in $jarFiles) {
    $hash = Get-SHA1 -filePath $file.FullName
    $sizeMB = [math]::Round($file.Length / 1MB, 2)
    $lastMod = $file.LastWriteTime.ToString("dd.MM.yyyy HH:mm:ss")
    $zoneId  = Get-ZoneIdentifier $file.FullName

    $modrinthData = Fetch-Modrinth -hash $hash
    if ($modrinthData.Slug) {
        $result.VerifiedMods += @{
            ModName  = $modrinthData.Name
            FileName = $file.Name
            Source   = "Modrinth"
            SizeMB   = $sizeMB
            LastMod  = $lastMod
        }
        continue
    }

    $megabaseData = Fetch-Megabase -hash $hash
    if ($megabaseData) {
        $result.VerifiedMods += @{
            ModName  = $megabaseData.name
            FileName = $file.Name
            Source   = "Megabase"
            SizeMB   = $sizeMB
            LastMod  = $lastMod
        }
        continue
    }

    $strings = Check-Strings $file.FullName
    if ($strings.Count -gt 0) {
        $result.CheatMods += @{
            FileName     = $file.Name
            FilePath     = $file.FullName
            DepFileName  = ""
            StringsFound = @($strings)
            SizeMB       = $sizeMB
            LastMod      = $lastMod
            ZoneId       = $zoneId
        }
        continue
    }

    $tempDir = Join-Path $env:TEMP "devyl_mod_$([System.IO.Path]::GetRandomFileName())"
    $cheatFoundInDep = $false
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
        [System.IO.Compression.ZipFile]::ExtractToDirectory($file.FullName, $tempDir)

        $depJarsPath = Join-Path $tempDir "META-INF/jars"
        if (Test-Path $depJarsPath) {
            foreach ($jar in (Get-ChildItem -Path $depJarsPath -Filter *.jar)) {
                $depStrings = Check-Strings $jar.FullName
                if ($depStrings.Count -gt 0) {
                    $result.CheatMods += @{
                        FileName     = $file.Name
                        FilePath     = $file.FullName
                        DepFileName  = $jar.Name
                        StringsFound = @($depStrings)
                        SizeMB       = $sizeMB
                        LastMod      = $lastMod
                        ZoneId       = $zoneId
                    }
                    $cheatFoundInDep = $true
                    break
                }
            }
        }
    } catch {} finally {
        if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue }
    }

    if (-not $cheatFoundInDep) {
        $result.UnknownMods += @{
            FileName = $file.Name
            FilePath = $file.FullName
            SizeMB   = $sizeMB
            LastMod  = $lastMod
            ZoneId   = $zoneId
        }
    }
}

$result | ConvertTo-Json -Depth 6
"""


class ModScanner:

    def run(self, mods_path: str = "") -> dict:
        try:
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix='.ps1', delete=False, encoding='utf-8'
            )
            tmp.write(MOD_SCANNER_PS_SCRIPT)
            tmp.close()

            cmd = [
                "powershell.exe",
                "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-File", tmp.name
            ]
            if mods_path:
                cmd += ["-ModsPath", mods_path]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            os.unlink(tmp.name)

            raw = result.stdout.strip()
            if not raw:
                return self._empty("No output from PowerShell")

            data = json.loads(raw)
            return self._parse(data)

        except json.JSONDecodeError as e:
            return self._empty(f"JSON error: {e}")
        except subprocess.TimeoutExpired:
            return self._empty("Scan timed out")
        except Exception as e:
            return self._empty(str(e))

    def _parse(self, data: dict) -> dict:
        def norm_list(v):
            if isinstance(v, dict): return [v]
            return v or []

        verified = []
        for m in norm_list(data.get("VerifiedMods")):
            verified.append({
                "mod_name": m.get("ModName", "Unknown"),
                "file_name": m.get("FileName", ""),
                "source":   m.get("Source", ""),
                "size_mb":  m.get("SizeMB", 0),
                "last_mod": m.get("LastMod", ""),
            })

        unknown = []
        for m in norm_list(data.get("UnknownMods")):
            unknown.append({
                "file_name": m.get("FileName", ""),
                "file_path": m.get("FilePath", ""),
                "size_mb":   m.get("SizeMB", 0),
                "last_mod":  m.get("LastMod", ""),
                "zone_id":   m.get("ZoneId") or "",
            })

        cheats = []
        for m in norm_list(data.get("CheatMods")):
            strings = m.get("StringsFound", [])
            if isinstance(strings, str): strings = [strings]
            cheats.append({
                "file_name":    m.get("FileName", ""),
                "file_path":    m.get("FilePath", ""),
                "dep_file":     m.get("DepFileName") or "",
                "strings_found": strings,
                "size_mb":      m.get("SizeMB", 0),
                "last_mod":     m.get("LastMod", ""),
                "zone_id":      m.get("ZoneId") or "",
            })

        return {
            "path_exists":        data.get("PathExists", False),
            "mods_path":          data.get("ModsPath", ""),
            "minecraft_running":  data.get("MinecraftRunning", False),
            "mc_start_time":      data.get("McStartTime", ""),
            "mc_uptime":          data.get("McUptime", ""),
            "verified_mods":      verified,
            "unknown_mods":       unknown,
            "cheat_mods":         cheats,
            "has_cheats":         len(cheats) > 0,
            "error":              data.get("Error", ""),
        }

    def _empty(self, error: str = "") -> dict:
        return {
            "path_exists": False, "mods_path": "",
            "minecraft_running": False, "mc_start_time": "", "mc_uptime": "",
            "verified_mods": [], "unknown_mods": [], "cheat_mods": [],
            "has_cheats": False, "error": error,
        }
