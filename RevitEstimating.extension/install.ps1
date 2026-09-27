param(
    [string]$TargetRoot = (Join-Path $env:APPDATA "pyRevit\Extensions"),
    [switch]$Uninstall,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$ExtensionName = "RevitEstimating.extension"
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Destination = Join-Path $TargetRoot $ExtensionName

function Get-UniqueSiblingPath {
    param([string]$BasePath, [string]$Suffix)
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $candidate = "$BasePath.$Suffix-$stamp"
    $index = 1
    while (Test-Path $candidate) {
        $candidate = "$BasePath.$Suffix-$stamp-$index"
        $index += 1
    }
    return $candidate
}

function Test-DeploymentIntegrity {
    param([string]$ExtensionPath)

    $manifestPath = Join-Path $ExtensionPath "deployment_manifest.json"
    if (-not (Test-Path $manifestPath)) {
        Write-Warning "deployment_manifest.json is absent. File-hash verification was skipped."
        return
    }

    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    if ($manifest.tool -ne "Revit Estimating Tools") {
        throw "Unexpected deployment manifest tool identity."
    }

    $declared = @{}
    foreach ($property in $manifest.files.PSObject.Properties) {
        $declared[$property.Name] = [string]$property.Value
    }

    foreach ($relative in $declared.Keys) {
        $nativeRelative = $relative.Replace("/", [IO.Path]::DirectorySeparatorChar)
        $path = Join-Path $ExtensionPath $nativeRelative
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Deployment file missing: $relative"
        }
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        if ($actual -ne $declared[$relative].ToLowerInvariant()) {
            throw "Deployment file hash mismatch: $relative"
        }
    }

    $actualFiles = Get-ChildItem -LiteralPath $ExtensionPath -Recurse -File | ForEach-Object {
        $_.FullName.Substring($ExtensionPath.Length).TrimStart("\","/").Replace("\","/")
    } | Where-Object {
        $_ -ne "deployment_manifest.json" -and
        $_ -notmatch "(^|/)__pycache__/" -and
        $_ -notmatch "\.(pyc|pyo)$"
    }

    foreach ($relative in $actualFiles) {
        if (-not $declared.ContainsKey($relative)) {
            throw "Undeclared deployment file: $relative"
        }
    }
}

if ($Uninstall) {
    if (-not (Test-Path -LiteralPath $Destination)) {
        Write-Host "Nothing to uninstall: $Destination"
        exit 0
    }
    $backup = Get-UniqueSiblingPath -BasePath $Destination -Suffix "uninstalled"
    if ($WhatIf) {
        Write-Host "WHATIF: Move $Destination -> $backup"
        exit 0
    }
    Move-Item -LiteralPath $Destination -Destination $backup
    Write-Host "Uninstalled safely. Previous extension preserved at:"
    Write-Host $backup
    exit 0
}

if (-not (Test-Path -LiteralPath (Join-Path $Source "extension.json") -PathType Leaf)) {
    throw "Run install.ps1 from inside a complete $ExtensionName folder."
}

Test-DeploymentIntegrity -ExtensionPath $Source

if ($WhatIf) {
    Write-Host "WHATIF: Install $Source -> $Destination"
    if (Test-Path -LiteralPath $Destination) {
        Write-Host "WHATIF: Existing installation would be backed up first."
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $TargetRoot)) {
    New-Item -ItemType Directory -Path $TargetRoot -Force | Out-Null
}

if (Test-Path -LiteralPath $Destination) {
    $backup = Get-UniqueSiblingPath -BasePath $Destination -Suffix "backup"
    Move-Item -LiteralPath $Destination -Destination $backup
    Write-Host "Existing installation backed up to:"
    Write-Host $backup
}

Copy-Item -LiteralPath $Source -Destination $Destination -Recurse
Test-DeploymentIntegrity -ExtensionPath $Destination

Write-Host "Installed successfully:"
Write-Host $Destination
Write-Host "Reload pyRevit before using the Estimating tab."
