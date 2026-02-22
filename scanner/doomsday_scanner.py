import subprocess
import json
import os
import sys
import tempfile


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_path, relative_path)


DOOMSDAY_PS_SCRIPT = r"""
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public class NtdllDecompressor {
    [DllImport("ntdll.dll")]
    public static extern uint RtlDecompressBufferEx(
        ushort CompressionFormat,
        byte[] UncompressedBuffer,
        int UncompressedBufferSize,
        byte[] CompressedBuffer,
        int CompressedBufferSize,
        out int FinalUncompressedSize,
        IntPtr WorkSpace
    );
    [DllImport("ntdll.dll")]
    public static extern uint RtlGetCompressionWorkSpaceSize(
        ushort CompressionFormat,
        out uint CompressBufferWorkSpaceSize,
        out uint CompressFragmentWorkSpaceSize
    );
    public static byte[] Decompress(byte[] compressed) {
        if (compressed.Length < 8) return null;
        if (compressed[0] != 0x4D || compressed[1] != 0x41 || compressed[2] != 0x4D) return null;
        int uncompSize = BitConverter.ToInt32(compressed, 4);
        uint wsComp, wsFrag;
        if (RtlGetCompressionWorkSpaceSize(4, out wsComp, out wsFrag) != 0) return null;
        IntPtr workspace = Marshal.AllocHGlobal((int)wsFrag);
        byte[] result = new byte[uncompSize];
        try {
            int finalSize;
            byte[] compData = new byte[compressed.Length - 8];
            Array.Copy(compressed, 8, compData, 0, compData.Length);
            uint status = RtlDecompressBufferEx(4, result, uncompSize, compData, compData.Length, out finalSize, workspace);
            if (status != 0) return null;
            return result;
        } finally {
            Marshal.FreeHGlobal(workspace);
        }
    }
}
"@

$BytePatterns = @(
    @{ Name = "Pattern #1"; Bytes = "6161370E160609949E0029033EA7000A2C1D03548403011D1008A1FFF6033EA7000A2B1D03548403011D07A1FFF710FEAC150599001A2A160C14005C6588B800" },
    @{ Name = "Pattern #2"; Bytes = "0C1504851D85160A6161370E160609949E0029033EA7000A2C1D03548403011D1008A1FFF6033EA7000A2B1D03548403011D07A1FFF710FEAC150599001A2A16" },
    @{ Name = "Pattern #3"; Bytes = "5910071088544C2A2BB8004D3B033DA7000A2B1C03548402011C1008A1FFF61A9E000C1A110800A2000503AC04AC00000000000A0005004E000101FA000001D3" }
)

$ClassPatterns = @(
    "net/java/f","net/java/g","net/java/h","net/java/i","net/java/k",
    "net/java/l","net/java/m","net/java/r","net/java/s","net/java/t","net/java/y"
)

function ConvertHex-ToBytes { param([string]$hexString)
    $bytes = New-Object byte[] ($hexString.Length / 2)
    for ($i = 0; $i -lt $hexString.Length; $i += 2) {
        $bytes[$i / 2] = [Convert]::ToByte($hexString.Substring($i, 2), 16)
    }
    return $bytes
}

function Search-BytePattern { param([byte[]]$data, [byte[]]$pattern)
    $pLen = $pattern.Length; $dLen = $data.Length
    for ($i = 0; $i -le ($dLen - $pLen); $i++) {
        $match = $true
        for ($j = 0; $j -lt $pLen; $j++) {
            if ($data[$i + $j] -ne $pattern[$j]) { $match = $false; break }
        }
        if ($match) { return $true }
    }
    return $false
}

function Search-ClassPattern { param([byte[]]$data, [string]$className)
    $classBytes = [System.Text.Encoding]::ASCII.GetBytes($className)
    return Search-BytePattern -data $data -pattern $classBytes
}

function Test-ZipMagicBytes { param([string]$Path)
    try {
        $fs = [System.IO.File]::OpenRead($Path)
        $r = New-Object System.IO.BinaryReader($fs)
        if ($fs.Length -lt 2) { $r.Close(); $fs.Close(); return $false }
        $b1 = $r.ReadByte(); $b2 = $r.ReadByte()
        $r.Close(); $fs.Close()
        return ($b1 -eq 0x50 -and $b2 -eq 0x4B)
    } catch { return $false }
}

function Get-PrefetchVersion { param([byte[]]$data)
    if ($data.Length -lt 8) { return 0 }
    $sig = [System.Text.Encoding]::ASCII.GetString($data, 4, 4)
    if ($sig -ne "SCCA") { return 0 }
    return [BitConverter]::ToUInt32($data, 0)
}

function Get-SystemIndexes { param([string]$FilePath)
    try {
        $data = [System.IO.File]::ReadAllBytes($FilePath)
        $isCompressed = ($data[0] -eq 0x4D -and $data[1] -eq 0x41 -and $data[2] -eq 0x4D)
        if ($isCompressed) {
            $data = [NtdllDecompressor]::Decompress($data)
            if ($data -eq $null) { return @() }
        }
        if ($data.Length -lt 108) { return @() }
        $version = Get-PrefetchVersion -data $data
        $sig = [System.Text.Encoding]::ASCII.GetString($data, 4, 4)
        if ($sig -ne "SCCA") { return @() }
        $stringsOffset = [BitConverter]::ToUInt32($data, 100)
        $stringsSize   = [BitConverter]::ToUInt32($data, 104)
        if ($stringsOffset -eq 0 -or $stringsSize -eq 0) { return @() }
        if ($stringsOffset -ge $data.Length -or ($stringsOffset + $stringsSize) -gt $data.Length) { return @() }
        $filenames = @()
        $pos = $stringsOffset; $endPos = $stringsOffset + $stringsSize
        while ($pos -lt $endPos -and $pos -lt $data.Length - 2) {
            $nullPos = $pos
            while ($nullPos -lt $data.Length - 1) {
                if ($data[$nullPos] -eq 0 -and $data[$nullPos + 1] -eq 0) { break }
                $nullPos += 2
            }
            if ($nullPos -gt $pos) {
                $strLen = $nullPos - $pos
                if ($strLen -gt 0 -and $strLen -lt 2048) {
                    try {
                        $fn = [System.Text.Encoding]::Unicode.GetString($data, $pos, $strLen)
                        if ($fn.Length -gt 0) { $filenames += $fn }
                    } catch {}
                }
            }
            $pos = $nullPos + 2
            if ($filenames.Count -gt 1000) { break }
        }
        return $filenames
    } catch { return @() }
}

function Find-SingleLetterClasses { param([string]$Path)
    $result = @()
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $jar = [System.IO.Compression.ZipFile]::OpenRead($Path)
        foreach ($entry in $jar.Entries) {
            if ($entry.FullName -like "*.class") {
                $parts = $entry.FullName -split '/'
                $classNameOnly = $parts[-1] -replace '\.class$', ''
                if ($classNameOnly -match '^[a-zA-Z]$') {
                    $fullPath = ($parts[0..($parts.Length-2)] -join '/') + '/' + $classNameOnly
                    $result += $fullPath
                }
            }
        }
        $jar.Dispose()
    } catch {}
    return $result
}

function Test-DoomsdayClient { param([string]$Path)
    $r = [PSCustomObject]@{
        IsDetected = $false; Confidence = "NONE"
        BytePatternMatches = @(); ClassNameMatches = @()
        SingleLetterClasses = @(); IsRenamedJar = $false; Error = $null
    }
    if (-not (Test-Path $Path -PathType Leaf)) { $r.Error = "File not found"; return $r }
    try {
        $ext = [System.IO.Path]::GetExtension($Path).ToLower()
        $hasPK = Test-ZipMagicBytes -Path $Path
        if ($hasPK -and $ext -ne ".jar") { $r.IsRenamedJar = $true; $r.IsDetected = $true; $r.Confidence = "HIGH" }
        if (-not $hasPK) { $r.Error = "Not a JAR/ZIP file"; return $r }
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $jar = [System.IO.Compression.ZipFile]::OpenRead($Path)
        $classFiles = $jar.Entries | Where-Object { $_.FullName -like "*.class" }
        $classCount = $classFiles.Count
        if ($classCount -gt 30) { $jar.Dispose(); $r.Error = "Skipped: Too many classes ($classCount)"; return $r }
        if ($classCount -eq 0) { $jar.Dispose(); $r.Error = "No .class files"; return $r }
        $allBytes = @()
        foreach ($entry in $classFiles) {
            $stream = $entry.Open()
            $reader = New-Object System.IO.BinaryReader($stream)
            $allBytes += $reader.ReadBytes([int]$entry.Length)
            $reader.Close(); $stream.Close()
        }
        $jar.Dispose()
        foreach ($pat in $BytePatterns) {
            $pb = ConvertHex-ToBytes -hexString $pat.Bytes
            if (Search-BytePattern -data $allBytes -pattern $pb) { $r.BytePatternMatches += $pat.Name }
        }
        foreach ($cn in $ClassPatterns) {
            if (Search-ClassPattern -data $allBytes -className $cn) { $r.ClassNameMatches += $cn }
        }
        $r.SingleLetterClasses = Find-SingleLetterClasses -Path $Path
        $bm = $r.BytePatternMatches.Count; $cm = $r.ClassNameMatches.Count; $sl = $r.SingleLetterClasses.Count
        if ($bm -ge 2) { $r.IsDetected = $true; $r.Confidence = "HIGH" }
        elseif ($bm -eq 1 -and ($cm -ge 5 -or $sl -ge 5)) { $r.IsDetected = $true; $r.Confidence = "MEDIUM" }
        elseif ($bm -eq 1) { $r.IsDetected = $true; $r.Confidence = "LOW" }
        elseif ($sl -ge 8 -and $cm -ge 3) { $r.IsDetected = $true; $r.Confidence = "MEDIUM" }
        elseif ($sl -ge 5 -or $cm -ge 5) { $r.IsDetected = $true; $r.Confidence = "LOW" }
        if ($r.IsRenamedJar -and $r.Confidence -eq "NONE") { $r.Confidence = "MEDIUM" }
    } catch { $r.Error = $_.Exception.Message }
    return $r
}

$runningJavaPaths = @()
try {
    $javaProcs = Get-Process -Name "java","javaw" -ErrorAction SilentlyContinue
    foreach ($proc in $javaProcs) {
        try {
            $procPath = $proc.MainModule.FileName
            if ($procPath) { $runningJavaPaths += $procPath }
        } catch {}
    }
} catch {}

$systemPath = "C:\Windows\Prefetch"
$javaFiles  = Get-ChildItem -Path $systemPath -Filter "JAVA*.EXE-*.pf" -ErrorAction SilentlyContinue

$allJarPaths  = @()
$fileMetadata = @{}

foreach ($sysFile in $javaFiles) {
    $indexes = Get-SystemIndexes -FilePath $sysFile.FullName
    foreach ($index in $indexes) {
        if ($index -match '\\VOLUME\{[^\}]+\}\\(.*)$') {
            $p = "C:\$($Matches[1])"
        } else { $p = $index }
        $allJarPaths += $p
        if (-not $fileMetadata.ContainsKey($p)) {
            $fileMetadata[$p] = @{ SourceFile = $sysFile.Name }
        }
    }
}

$allDrives = Get-PSDrive -PSProvider FileSystem |
    Where-Object { $_.Root -match '^[A-Z]:\\$' } |
    ForEach-Object { $_.Root.Substring(0, 1) }

$detections  = @()
$scannedPaths = @()

foreach ($path in ($allJarPaths | Select-Object -Unique)) {
    $foundPath = $null
    if (Test-Path $path -PathType Leaf) { $foundPath = $path }
    else {
        if ($path -match '^[A-Z]:\\(.*)$') {
            $rel = $Matches[1]
            foreach ($drv in $allDrives) {
                $tp = "$drv`:\$rel"
                if (Test-Path $tp -PathType Leaf) { $foundPath = $tp; break }
            }
        }
    }
    if (-not $foundPath) { continue }

    $size = (Get-Item $foundPath -EA SilentlyContinue).Length
    if ($size -lt 200KB -or $size -gt 15MB) { continue }

    $scannedPaths += $foundPath
    $res = Test-DoomsdayClient -Path $foundPath
    if ($res.IsDetected) {
        $isRunning = $false
        foreach ($rp in $runningJavaPaths) {
            if ($rp -like "*$([System.IO.Path]::GetFileName($foundPath))*") { $isRunning = $true; break }
        }
        $detections += @{
            Path            = $foundPath
            Confidence      = $res.Confidence
            IsRenamedJar    = $res.IsRenamedJar
            BytePatterns    = $res.BytePatternMatches.Count
            ClassMatches    = $res.ClassNameMatches.Count
            SingleLetterCls = $res.SingleLetterClasses.Count
            IsRunning       = $isRunning
            SourcePrefetch  = $fileMetadata[$path].SourceFile
        }
    }
}

$output = @{
    Detections    = $detections
    ScannedCount  = $scannedPaths.Count
    RunningJava   = $runningJavaPaths
}

$output | ConvertTo-Json -Depth 5
"""


class DoomsdayScanner:

    def run(self) -> dict:
        try:
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix='.ps1', delete=False, encoding='utf-8'
            )
            tmp.write(DOOMSDAY_PS_SCRIPT)
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
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            os.unlink(tmp.name)

            raw = result.stdout.strip()
            if not raw:
                return self._empty_result("No output from PowerShell")

            data = json.loads(raw)
            return self._parse_result(data)

        except json.JSONDecodeError as e:
            return self._empty_result(f"JSON parse error: {e}")
        except subprocess.TimeoutExpired:
            return self._empty_result("Scan timed out")
        except Exception as e:
            return self._empty_result(str(e))

    def _parse_result(self, data: dict) -> dict:
        detections = data.get("Detections", []) or []
        scanned    = data.get("ScannedCount", 0)

        if isinstance(detections, dict):
            detections = [detections]

        found = []
        for d in detections:
            found.append({
                "name":          "Doomsday Client",
                "path":          d.get("Path", "Unknown"),
                "confidence":    d.get("Confidence", "UNKNOWN"),
                "is_renamed_jar": bool(d.get("IsRenamedJar", False)),
                "byte_patterns": int(d.get("BytePatterns", 0)),
                "class_matches": int(d.get("ClassMatches", 0)),
                "single_letter_classes": int(d.get("SingleLetterCls", 0)),
                "is_running":    bool(d.get("IsRunning", False)),
                "source_prefetch": d.get("SourcePrefetch", ""),
                "level":         "Suspicious",
                "status":        "In Use" if d.get("IsRunning") else "Found",
            })

        return {
            "detections":   found,
            "scanned_count": scanned,
            "detected":     len(found) > 0,
        }

    def _empty_result(self, error: str = "") -> dict:
        return {
            "detections":    [],
            "scanned_count": 0,
            "detected":      False,
            "error":         error,
        }
