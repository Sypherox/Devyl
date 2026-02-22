import subprocess
import json
import os
import tempfile
import sys


UNSIGNED_PS_SCRIPT = r"""
$directories = @(
    "$env:windir\System32",
    "$env:windir\SysWOW64",
    "$env:USERPROFILE\AppData\Local\Temp"
)

$microsoftRegex = [regex]::new('Microsoft|Windows|Redmond',
    [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor
    [System.Text.RegularExpressions.RegexOptions]::Compiled)

$trustedRegex = [regex]::new(
    'NVIDIA|Intel|AMD|Realtek|VIA|Qualcomm|Razer|Lenovo|Dolby|HP Inc|Dell Inc|ASUS|Acer|Logitech|Corsair',
    [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor
    [System.Text.RegularExpressions.RegexOptions]::Compiled)

$knownCheatRegex = [regex]::new('manthe',
    [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor
    [System.Text.RegularExpressions.RegexOptions]::Compiled)

$knownGoodFiles = @{
    'ntoskrnl.exe' = $true; 'kernel32.dll' = $true; 'user32.dll' = $true
    'advapi32.dll' = $true; 'shell32.dll'  = $true; 'explorer.exe' = $true
    'svchost.exe'  = $true; 'services.exe' = $true; 'lsass.exe'    = $true
    'csrss.exe'    = $true; 'winlogon.exe' = $true; 'dwm.exe'      = $true
}

$nonExecExt = @('.evtx','.etl','.dat','.db','.log','.log1','.log2',
                '.regtrans-ms','.blf','.cab','.rtf','.inf','.txt',
                '.tmp','.bin','.bak','.btx','.btr','.wal','.xml',
                '.db-wal','.mui')

$signatureCache = @{}

function Test-ShouldIncludeFile {
    param([System.IO.FileInfo]$FileInfo)
    try {
        $fileName = $FileInfo.Name
        $ext      = $FileInfo.Extension.ToLower()
        if ($nonExecExt -contains $ext) { return $false }

        try {
            $stream    = [System.IO.File]::OpenRead($FileInfo.FullName)
            $buffer    = New-Object byte[] 2
            $bytesRead = $stream.Read($buffer, 0, 2)
            $stream.Close()
            if ($bytesRead -lt 2 -or $buffer[0] -ne 0x4D -or $buffer[1] -ne 0x5A) { return $false }
        } catch { return $false }

        if ($fileName -match '^(microsoft|windows|ms)') { return $false }
        if ($knownGoodFiles.ContainsKey($fileName.ToLower()))  { return $false }

        $filePath = $FileInfo.FullName
        $sigResult = "unsigned"

        if ($signatureCache.ContainsKey($filePath)) {
            $sigResult = $signatureCache[$filePath]
        } else {
            try {
                $sig = Get-AuthenticodeSignature -FilePath $filePath -ErrorAction Stop
                if ($sig.Status -eq "Valid" -and $sig.SignerCertificate) {
                    $subject = $sig.SignerCertificate.Subject
                    if ($knownCheatRegex.IsMatch($subject)) {
                        $sigResult = "cheat"
                    } elseif ($microsoftRegex.IsMatch($subject) -or $trustedRegex.IsMatch($subject)) {
                        $sigResult = "trusted"
                    } else {
                        $sigResult = "unknown_signer"
                    }
                } else {
                    $sigResult = "unsigned"
                }
            } catch { $sigResult = "unsigned" }
            $signatureCache[$filePath] = $sigResult
        }

        if ($sigResult -eq "trusted") { return $false }

        try {
            $vi = $FileInfo.VersionInfo
            if ($vi.CompanyName) {
                if ($microsoftRegex.IsMatch($vi.CompanyName) -or $trustedRegex.IsMatch($vi.CompanyName)) {
                    return $false
                }
            }
        } catch {}

        return $true
    } catch { return $false }
}

function Get-SignerInfo {
    param([string]$FilePath)
    try {
        $sig = Get-AuthenticodeSignature -FilePath $FilePath -ErrorAction Stop
        if ($sig.Status -eq "Valid" -and $sig.SignerCertificate) {
            return @{
                Status  = $sig.Status.ToString()
                Subject = $sig.SignerCertificate.Subject
                IsCheat = $knownCheatRegex.IsMatch($sig.SignerCertificate.Subject)
            }
        }
        return @{ Status = $sig.Status.ToString(); Subject = ""; IsCheat = $false }
    } catch {
        return @{ Status = "Error"; Subject = ""; IsCheat = $false }
    }
}

$results    = @{ UnsignedFiles = @(); CheatFiles = @(); ScannedCount = 0 }
$cheatFiles = @()
$unsignedFiles = @()
$totalChecked  = 0

foreach ($directory in $directories) {
    if (-not (Test-Path $directory)) { continue }

    try {
        $files = Get-ChildItem -Path $directory -File -Recurse -Force -ErrorAction SilentlyContinue |
                 Where-Object { $_.Length -ge 300KB }

        foreach ($fileInfo in $files) {
            try {
                $totalChecked++
                if (-not (Test-ShouldIncludeFile -FileInfo $fileInfo)) { continue }

                $sigInfo  = Get-SignerInfo -FilePath $fileInfo.FullName
                $sizeMB   = [math]::Round($fileInfo.Length / 1MB, 2)
                $lastMod  = $fileInfo.LastWriteTime.ToString("dd.MM.yyyy HH:mm:ss")

                $entry = @{
                    Path       = $fileInfo.FullName
                    Name       = $fileInfo.Name
                    SizeMB     = $sizeMB
                    LastMod    = $lastMod
                    SigStatus  = $sigInfo.Status
                    Signer     = $sigInfo.Subject
                    Directory  = $directory
                }

                if ($sigInfo.IsCheat) {
                    $cheatFiles += $entry
                } else {
                    $unsignedFiles += $entry
                }
            } catch { continue }
        }
    } catch { continue }
}

$results.UnsignedFiles = $unsignedFiles
$results.CheatFiles    = $cheatFiles
$results.ScannedCount  = $totalChecked

$results | ConvertTo-Json -Depth 5
"""


class UnsignedScanner:

    def run(self) -> dict:
        try:
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix='.ps1', delete=False, encoding='utf-8'
            )
            tmp.write(UNSIGNED_PS_SCRIPT)
            tmp.close()

            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy", "Bypass",
                    "-File", tmp.name
                ],
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            os.unlink(tmp.name)

            raw = result.stdout.strip()
            if not raw:
                return self._empty("No output from PowerShell")

            data = json.loads(raw)
            return self._parse(data)

        except json.JSONDecodeError as e:
            return self._empty(f"JSON parse error: {e}")
        except subprocess.TimeoutExpired:
            return self._empty("Scan timed out (>5min)")
        except Exception as e:
            return self._empty(str(e))

    def _parse(self, data: dict) -> dict:
        cheat_raw    = data.get("CheatFiles", []) or []
        unsigned_raw = data.get("UnsignedFiles", []) or []
        scanned      = data.get("ScannedCount", 0)

        if isinstance(cheat_raw, dict):    cheat_raw    = [cheat_raw]
        if isinstance(unsigned_raw, dict): unsigned_raw = [unsigned_raw]

        cheat_files = []
        for f in cheat_raw:
            cheat_files.append({
                "name":       f.get("Name", "Unknown"),
                "path":       f.get("Path", "Unknown"),
                "size_mb":    f.get("SizeMB", 0),
                "last_mod":   f.get("LastMod", ""),
                "sig_status": f.get("SigStatus", ""),
                "signer":     f.get("Signer", ""),
                "directory":  f.get("Directory", ""),
                "suspicious": True,
                "last_run":   f.get("LastMod", ""),
            })

        unsigned_files = []
        for f in unsigned_raw:
            unsigned_files.append({
                "name":       f.get("Name", "Unknown"),
                "path":       f.get("Path", "Unknown"),
                "size_mb":    f.get("SizeMB", 0),
                "last_mod":   f.get("LastMod", ""),
                "sig_status": f.get("SigStatus", ""),
                "signer":     f.get("Signer", ""),
                "directory":  f.get("Directory", ""),
            })

        return {
            "cheat_files":    cheat_files,
            "unsigned_files": unsigned_files,
            "scanned_count":  scanned,
            "has_cheats":     len(cheat_files) > 0,
        }

    def _empty(self, error: str = "") -> dict:
        return {
            "cheat_files":    [],
            "unsigned_files": [],
            "scanned_count":  0,
            "has_cheats":     False,
            "error":          error,
        }
