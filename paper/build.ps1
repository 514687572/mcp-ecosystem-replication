<#
    Build the manuscript: pdflatex -> bibtex -> pdflatex x2.

    Usage:
      powershell -ExecutionPolicy Bypass -File paper\build.ps1
#>
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$root = Split-Path -Parent $PSScriptRoot
$tex  = Join-Path $root "paper\latex"

Write-Host "checking citations and cross-references" -ForegroundColor Cyan
python (Join-Path $root "paper\check_citations.py")

Write-Host "`nJSS format checks" -ForegroundColor Cyan
python (Join-Path $root "paper\check_format.py")

Write-Host "`nstyle metrics" -ForegroundColor Cyan
python (Join-Path $root "paper\ai_style_check.py")

Push-Location $tex
try {
    # MiKTeX writes an administrative "updates out-of-sync" notice to stderr on
    # every run. It is not a build failure, so stderr must not terminate the
    # script; the log is inspected for real errors afterwards instead.
    $ErrorActionPreference = "Continue"

    Write-Host "`npass 1" -ForegroundColor Cyan
    pdflatex -interaction=nonstopmode mcp-ecosystem.tex 2>&1 | Out-Null
    Write-Host "bibtex" -ForegroundColor Cyan
    bibtex mcp-ecosystem 2>&1 | Out-Null
    Write-Host "pass 2" -ForegroundColor Cyan
    pdflatex -interaction=nonstopmode mcp-ecosystem.tex 2>&1 | Out-Null
    Write-Host "pass 3" -ForegroundColor Cyan
    pdflatex -interaction=nonstopmode mcp-ecosystem.tex 2>&1 | Out-Null

    $log = Get-Content mcp-ecosystem.log -Raw
    $undefined = ([regex]::Matches($log, "Citation .* undefined")).Count
    $pages = ([regex]::Match($log, "Output written on .*\((\d+) pages")).Groups[1].Value
    $overfull = ([regex]::Matches($log, "Overfull \\hbox")).Count
    $errors = ([regex]::Matches($log, "^! ", "Multiline")).Count

    Write-Host "`nresult" -ForegroundColor Green
    Write-Host ("  pages              : {0}" -f $pages)
    Write-Host ("  undefined citations: {0}" -f $undefined)
    Write-Host ("  overfull hboxes    : {0}" -f $overfull)
    Write-Host ("  LaTeX errors       : {0}" -f $errors)
    Write-Host ("  pdf                : {0}" -f (Join-Path $tex "mcp-ecosystem.pdf"))
}
finally {
    Pop-Location
}
