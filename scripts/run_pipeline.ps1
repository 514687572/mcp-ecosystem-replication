<#
    Full pipeline, in order. Each step is resumable, so re-running the script
    after an interruption continues rather than starting over.

    Usage:
      powershell -ExecutionPolicy Bypass -File scripts\run_pipeline.ps1
      powershell -ExecutionPolicy Bypass -File scripts\run_pipeline.ps1 -SkipGitHub

    Set $env:GITHUB_TOKEN first to make the GitHub step practical.
#>
param(
    [switch]$SkipGitHub,
    [switch]$SkipPackages,
    [switch]$SkipTools,
    [int]$ToolSample = 1200
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

function Step($name, $block) {
    Write-Host ""
    Write-Host ("=" * 72) -ForegroundColor DarkGray
    Write-Host " $name" -ForegroundColor Cyan
    Write-Host ("=" * 72) -ForegroundColor DarkGray
    & $block
    if ($LASTEXITCODE -ne 0) { throw "step failed: $name" }
}

Step "1/6  harvest the official MCP registry" {
    python scripts\01_harvest_registry.py
}

Step "2/6  registry census tables and figures" {
    python scripts\02_analyze_registry.py
}

if (-not $SkipPackages) {
    Step "3/6  enrich packages (npm / PyPI metadata)" {
        python scripts\03_enrich_packages.py
    }
}

if (-not $SkipTools) {
    Step "4/6  extract tool definitions from package sources" {
        python scripts\04_extract_tools.py --sample $ToolSample
    }
}

if (-not $SkipGitHub) {
    Step "5/6  enrich GitHub repositories" {
        python scripts\05_enrich_github.py
    }
}

Step "6/6  cross-source analysis" {
    python scripts\06_cross_analysis.py
}

Step "manifest" {
    python scripts\07_manifest.py
}

Write-Host ""
Write-Host "pipeline finished. Tables in results/tables, figures in results/figures." -ForegroundColor Green
