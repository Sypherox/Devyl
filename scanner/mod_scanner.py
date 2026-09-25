import subprocess
import json
import os
import tempfile


MOD_SCANNER_PS_SCRIPT = r"""
param(
    [string]$ModsPath = "",
    [string]$VirusTotalApiKey = ""
)

if (-not $ModsPath) {
    $ModsPath = "$env:USERPROFILE\AppData\Roaming\.minecraft\mods"
}

$SizeTolerancePercent = 2
$KnownCheatConfigFolders = @(
    "wurst", "meteor-client", "impactclient", "kami-blue", "novoline",
    "aristois", "sigma", "salhack", "flux", "ares", "rusherhack",
    "wolfram", "kirin", "matrix", "yaphet", "future-client", "Prestige"
)

$result = @{
    ModsPath          = $ModsPath
    PathExists        = $false
    VerifiedMods      = @()
    ModifiedMods      = @()
    SpoofedMods       = @()
    UnknownMods       = @()
    CheatMods         = @()
    ObfuscatedMods    = @()
    CheatConfigsFound = @()
    MinecraftRunning  = $false
    McStartTime       = ""
    McUptime          = ""
    Error             = ""
}

if (-not (Test-Path $ModsPath -PathType Container)) {
    $result.Error = "Mods folder not found: $ModsPath"
    $result | ConvertTo-Json -Depth 6
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

$mcRoot = Split-Path -Parent $ModsPath
foreach ($folder in $KnownCheatConfigFolders) {
    $candidatePaths = @(
        (Join-Path $mcRoot $folder),
        (Join-Path (Join-Path $mcRoot "config") $folder)
    )
    foreach ($cp in $candidatePaths) {
        if (Test-Path $cp) {
            $result.CheatConfigsFound += @{
                FolderName = $folder
                Path       = $cp
            }
        }
    }
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
    "AntiFireball", "BowAimbot", "ESP"
)

function Get-FileHashHex {
    param([string]$filePath, [string]$Algo = "SHA1")
    return (Get-FileHash -Path $filePath -Algorithm $Algo).Hash.ToLower()
}

function Get-ZoneIdentifier {
    param([string]$filePath)
    $ads = Get-Content -Raw -Stream Zone.Identifier $filePath -ErrorAction SilentlyContinue
    if ($ads -match "HostUrl=(.+)") { return $matches[1].Trim() }
    return $null
}

function Fetch-ModrinthByHash {
    param([string]$hash)
    try {
        $r = Invoke-RestMethod -Uri "https://api.modrinth.com/v2/version_file/$hash" `
             -Method Get -UseBasicParsing -ErrorAction Stop -TimeoutSec 5
        if ($r.project_id) {
            $p = Invoke-RestMethod -Uri "https://api.modrinth.com/v2/project/$($r.project_id)" `
                 -Method Get -UseBasicParsing -ErrorAction Stop -TimeoutSec 5
            return @{
                Name       = $p.title
                Slug       = $p.slug
                ProjectId  = $r.project_id
                VersionId  = $r.id
                Datepub    = $r.date_published
                MatchedFile = ($r.files | Where-Object { $_.hashes.sha1 -eq $hash } | Select-Object -First 1)
            }
        }
    } catch {}
    return $null
}

function Search-ModrinthByName {
    param([string]$fileName)
    $clean = $fileName -replace '\.jar$', '' -replace '[-_]?(fabric|forge|neoforge|quilt)', '' -replace '[-_]?\d+(\.\d+)+.*$', ''
    $clean = $clean -replace '[-_]', ' '
    $clean = $clean.Trim()
    if (-not $clean) { return $null }
    try {
        $encoded = [uri]::EscapeDataString($clean)
        $r = Invoke-RestMethod -Uri "https://api.modrinth.com/v2/search?query=$encoded&limit=3" `
             -Method Get -UseBasicParsing -ErrorAction Stop -TimeoutSec 5
        if ($r.hits -and $r.hits.Count -gt 0) {
            return $r.hits[0]
        }
    } catch {}
    return $null
}

function Get-AllVersionSizesForProject {
    param([string]$projectId)
    $sizes = [System.Collections.Generic.List[object]]::new()
    try {
        $versions = Invoke-RestMethod -Uri "https://api.modrinth.com/v2/project/$projectId/version" `
                    -Method Get -UseBasicParsing -ErrorAction Stop -TimeoutSec 8
        foreach ($v in $versions) {
            foreach ($f in $v.files) {
                $sizes.Add(@{
                    Size          = $f.size
                    FileName      = $f.filename
                    VersionNumber = $v.version_number
                    DatePublished = $v.date_published
                    Sha1          = $f.hashes.sha1
                })
            }
        }
    } catch {}
    return $sizes
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

function Fetch-VirusTotal {
    param([string]$sha256, [string]$ApiKey)
    if (-not $ApiKey) { return $null }
    try {
        $headers = @{ "x-apikey" = $ApiKey }
        $r = Invoke-RestMethod -Uri "https://www.virustotal.com/api/v3/files/$sha256" `
             -Method Get -Headers $headers -ErrorAction Stop -TimeoutSec 8
        $attr = $r.data.attributes
        $stats = $attr.last_analysis_stats
        return @{
            Malicious      = $stats.malicious
            Suspicious     = $stats.suspicious
            TotalEngines   = ($stats.malicious + $stats.suspicious + $stats.undetected + $stats.harmless)
            KnownNames     = @($attr.names | Select-Object -Unique)
            FirstSubmitted = if ($attr.first_submission_date) { [DateTimeOffset]::FromUnixTimeSeconds($attr.first_submission_date).ToString("dd.MM.yyyy") } else { "" }
            Reputation     = $attr.reputation
        }
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

function Analyze-JarStructure {
    param([string]$filePath)
    $info = @{
        HasFabricJson       = $false
        HasForgeToml        = $false
        ModId               = ""
        ModName             = ""
        ModVersionDeclared  = ""
        ClassCount          = 0
        ShortNameClassCount = 0
        ObfuscationRatio    = 0.0
        IsSigned            = $false
        TopLevelPackages    = @()
    }
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zip = [System.IO.Compression.ZipFile]::OpenRead($filePath)
        $classEntries = $zip.Entries | Where-Object { $_.FullName -like "*.class" -and $_.FullName -notlike "META-INF/*" }
        $info.ClassCount = $classEntries.Count

        $shortCount = 0
        $pkgSet = New-Object System.Collections.Generic.HashSet[string]
        foreach ($e in $classEntries) {
            $leaf = ($e.FullName -split '/')[-1] -replace '\.class$', ''
            if ($leaf -match '^[A-Za-z]{1,2}$') { $shortCount++ }
            $parts = $e.FullName -split '/'
            if ($parts.Length -gt 1) { [void]$pkgSet.Add($parts[0]) }
        }
        $info.ShortNameClassCount = $shortCount
        if ($info.ClassCount -gt 0) {
            $info.ObfuscationRatio = [math]::Round(($shortCount / $info.ClassCount) * 100, 1)
        }
        $info.TopLevelPackages = @($pkgSet)

        $signEntry = $zip.Entries | Where-Object { $_.FullName -like "META-INF/*.RSA" -or $_.FullName -like "META-INF/*.SF" }
        $info.IsSigned = ($signEntry.Count -gt 0)

        $fabricEntry = $zip.Entries | Where-Object { $_.FullName -eq "fabric.mod.json" } | Select-Object -First 1
        if ($fabricEntry) {
            $info.HasFabricJson = $true
            $sr = New-Object System.IO.StreamReader($fabricEntry.Open())
            $jsonText = $sr.ReadToEnd()
            $sr.Close()
            try {
                $j = $jsonText | ConvertFrom-Json
                $info.ModId = $j.id
                $info.ModName = $j.name
                $info.ModVersionDeclared = $j.version
            } catch {}
        }

        $tomlEntry = $zip.Entries | Where-Object { $_.FullName -eq "META-INF/mods.toml" -or $_.FullName -eq "META-INF/neoforge.mods.toml" } | Select-Object -First 1
        if ($tomlEntry) {
            $info.HasForgeToml = $true
            $sr = New-Object System.IO.StreamReader($tomlEntry.Open())
            $tomlText = $sr.ReadToEnd()
            $sr.Close()
            if ($tomlText -match 'modId\s*=\s*"([^"]+)"') { $info.ModId = $matches[1] }
            if ($tomlText -match 'displayName\s*=\s*"([^"]+)"') { $info.ModName = $matches[1] }
            if ($tomlText -match 'version\s*=\s*"([^"]+)"') { $info.ModVersionDeclared = $matches[1] }
        }

        $zip.Dispose()
    } catch {}
    return $info
}

function Test-TimestampAnomaly {
    param([string]$filePath, [string]$datePublishedIso)
    if (-not $datePublishedIso) { return $false }
    try {
        $published = [datetime]$datePublishedIso
        $lastWrite = (Get-Item $filePath).LastWriteTime
        return ($lastWrite -gt $published.AddDays(3))
    } catch { return $false }
}

$jarFiles = Get-ChildItem -Path $ModsPath -Filter *.jar -ErrorAction SilentlyContinue

foreach ($file in $jarFiles) {
    $sha1 = Get-FileHashHex -filePath $file.FullName -Algo "SHA1"
    $sha256 = Get-FileHashHex -filePath $file.FullName -Algo "SHA256"
    $sizeBytes = $file.Length
    $sizeMB = [math]::Round($sizeBytes / 1MB, 2)
    $lastMod = $file.LastWriteTime.ToString("dd.MM.yyyy HH:mm:ss")
    $zoneId  = Get-ZoneIdentifier $file.FullName
    $structure = Analyze-JarStructure -filePath $file.FullName

    $baseEntry = @{
        FileName         = $file.Name
        FilePath         = $file.FullName
        SizeMB           = $sizeMB
        SizeBytes        = $sizeBytes
        LastMod          = $lastMod
        ZoneId           = $zoneId
        Sha1             = $sha1
        Sha256           = $sha256
        ModId            = $structure.ModId
        ClassCount       = $structure.ClassCount
        ObfuscationRatio = $structure.ObfuscationRatio
        IsSigned         = $structure.IsSigned
    }

    $hashMatch = Fetch-ModrinthByHash -hash $sha1
    if ($hashMatch) {
        $entry = $baseEntry.Clone()
        $entry.ModName = $hashMatch.Name
        $entry.Source  = "Modrinth (Hash-Match)"
        $entry.Status  = "Verified"

        if (Test-TimestampAnomaly -filePath $file.FullName -datePublishedIso $hashMatch.Datepub) {
            $entry.Status = "Verified - Timestamp Anomaly"
        }
        $result.VerifiedMods += $entry
        continue
    }

    $searchHit = Search-ModrinthByName -fileName $file.Name
    if ($searchHit) {
        $allSizes = Get-AllVersionSizesForProject -projectId $searchHit.project_id
        $matchWithinTolerance = $false
        $closestDiffPercent = 999
        foreach ($v in $allSizes) {
            if ($v.Size -gt 0) {
                $diffPercent = [math]::Abs($sizeBytes - $v.Size) / $v.Size * 100
                if ($diffPercent -lt $closestDiffPercent) { $closestDiffPercent = $diffPercent }
                if ($diffPercent -le $SizeTolerancePercent) { $matchWithinTolerance = $true }
            }
        }

        $entry = $baseEntry.Clone()
        $entry.ModName = $searchHit.title
        $entry.Source  = "Modrinth (Name-Match: $($searchHit.slug))"
        $entry.ClosestSizeDiffPercent = [math]::Round($closestDiffPercent, 1)

        if ($matchWithinTolerance) {
            $entry.Status = "Modified - Size OK (andere Version/Loader)"
            $result.ModifiedMods += $entry
            continue
        } else {
            if ($structure.ObfuscationRatio -ge 40) {
                $entry.Status = "Spoofed file size (+ obfuszierter Code, $($structure.ObfuscationRatio)% kurze Klassennamen)"
            } else {
                $entry.Status = "Spoofed file size / Renamed"
            }
            $result.SpoofedMods += $entry
            continue
        }
    }

    $strings = Check-Strings $file.FullName
    if ($strings.Count -gt 0) {
        $entry = $baseEntry.Clone()
        $entry.DepFileName = ""
        $entry.StringsFound = @($strings)
        $result.CheatMods += $entry
        continue
    }

    $tempDir = Join-Path $env:TEMP "devyl_mod_$([System.IO.Path]::GetRandomFileName())"
    $cheatFoundInDep = $false
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
        [System.IO.Compression.ZipFile]::ExtractToDirectory($file.FullName, $tempDir)

        $nestedJars = Get-ChildItem -Path $tempDir -Filter *.jar -Recurse -ErrorAction SilentlyContinue
        foreach ($jar in $nestedJars) {
            $depStrings = Check-Strings $jar.FullName
            if ($depStrings.Count -gt 0) {
                $entry = $baseEntry.Clone()
                $entry.DepFileName = $jar.Name
                $entry.StringsFound = @($depStrings)
                $result.CheatMods += $entry
                $cheatFoundInDep = $true
                break
            }
        }
    } catch {} finally {
        if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue }
    }
    if ($cheatFoundInDep) { continue }

    if ($structure.ObfuscationRatio -ge 60 -and $structure.ClassCount -ge 5) {
        $entry = $baseEntry.Clone()
        $entry.Reason = "Hoher Obfuskierungs-Anteil ($($structure.ObfuscationRatio)% Klassen mit 1-2 Buchstaben Namen), Mod bei Modrinth unbekannt"
        $result.ObfuscatedMods += $entry
        continue
    }

    $vt = Fetch-VirusTotal -sha256 $sha256 -ApiKey $VirusTotalApiKey
    $entry = $baseEntry.Clone()
    if ($vt) {
        $entry.VtMalicious      = $vt.Malicious
        $entry.VtSuspicious     = $vt.Suspicious
        $entry.VtTotalEngines   = $vt.TotalEngines
        $entry.VtKnownNames     = $vt.KnownNames
        $entry.VtFirstSubmitted = $vt.FirstSubmitted
        $entry.VtReputation     = $vt.Reputation
    }
    $result.UnknownMods += $entry
}

$result | ConvertTo-Json -Depth 8
"""


class ModScanner:
    def run(self, mods_path: str = "") -> dict:
        try:
            try:
                from config import VIRUSTOTAL_API_KEY
            except ImportError:
                VIRUSTOTAL_API_KEY = ""

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
            if VIRUSTOTAL_API_KEY:
                cmd += ["-VirusTotalApiKey", VIRUSTOTAL_API_KEY]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=240,
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

    @staticmethod
    def _norm_list(v):
        if isinstance(v, dict):
            return [v]
        return v or []

    def _base_fields(self, m: dict) -> dict:
        strings = m.get("StringsFound", [])
        if isinstance(strings, str):
            strings = [strings]
        known_names = m.get("VtKnownNames", [])
        if isinstance(known_names, str):
            known_names = [known_names]
        top_packages = m.get("TopLevelPackages", [])
        if isinstance(top_packages, str):
            top_packages = [top_packages]

        return {
            "file_name":           m.get("FileName", ""),
            "file_path":           m.get("FilePath", ""),
            "mod_name":            m.get("ModName", ""),
            "mod_id":              m.get("ModId", ""),
            "source":              m.get("Source", ""),
            "status":              m.get("Status", ""),
            "size_mb":             m.get("SizeMB", 0),
            "size_bytes":          m.get("SizeBytes", 0),
            "last_mod":            m.get("LastMod", ""),
            "zone_id":             m.get("ZoneId") or "",
            "sha1":                m.get("Sha1", ""),
            "sha256":              m.get("Sha256", ""),
            "class_count":         m.get("ClassCount", 0),
            "obfuscation_ratio":   m.get("ObfuscationRatio", 0.0),
            "is_signed":           m.get("IsSigned", False),
            "closest_size_diff_percent": m.get("ClosestSizeDiffPercent", None),
            "dep_file":            m.get("DepFileName") or "",
            "strings_found":       strings,
            "reason":              m.get("Reason", ""),
            "vt_malicious":        m.get("VtMalicious", None),
            "vt_suspicious":       m.get("VtSuspicious", None),
            "vt_total_engines":    m.get("VtTotalEngines", None),
            "vt_known_names":      known_names,
            "vt_first_submitted":  m.get("VtFirstSubmitted", ""),
            "vt_reputation":       m.get("VtReputation", None),
        }

    def _parse(self, data: dict) -> dict:
        verified   = [self._base_fields(m) for m in self._norm_list(data.get("VerifiedMods"))]
        modified   = [self._base_fields(m) for m in self._norm_list(data.get("ModifiedMods"))]
        spoofed    = [self._base_fields(m) for m in self._norm_list(data.get("SpoofedMods"))]
        unknown    = [self._base_fields(m) for m in self._norm_list(data.get("UnknownMods"))]
        cheats     = [self._base_fields(m) for m in self._norm_list(data.get("CheatMods"))]
        obfuscated = [self._base_fields(m) for m in self._norm_list(data.get("ObfuscatedMods"))]

        cheat_configs = []
        for c in self._norm_list(data.get("CheatConfigsFound")):
            cheat_configs.append({
                "folder_name": c.get("FolderName", ""),
                "path":        c.get("Path", ""),
            })

        has_cheats = len(cheats) > 0 or len(spoofed) > 0 or len(obfuscated) > 0 or len(cheat_configs) > 0

        return {
            "path_exists":        data.get("PathExists", False),
            "mods_path":          data.get("ModsPath", ""),
            "minecraft_running":  data.get("MinecraftRunning", False),
            "mc_start_time":      data.get("McStartTime", ""),
            "mc_uptime":          data.get("McUptime", ""),
            "verified_mods":      verified,
            "modified_mods":      modified,
            "spoofed_mods":       spoofed,
            "unknown_mods":       unknown,
            "cheat_mods":         cheats,
            "obfuscated_mods":    obfuscated,
            "cheat_configs_found": cheat_configs,
            "has_cheats":         has_cheats,
            "error":              data.get("Error", ""),
        }

    def _empty(self, error: str = "") -> dict:
        return {
            "path_exists": False, "mods_path": "",
            "minecraft_running": False, "mc_start_time": "", "mc_uptime": "",
            "verified_mods": [], "modified_mods": [], "spoofed_mods": [],
            "unknown_mods": [], "cheat_mods": [], "obfuscated_mods": [],
            "cheat_configs_found": [],
            "has_cheats": False, "error": error,
        }
