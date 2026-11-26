# Prism project guide: open the key files, then the explainer in the browser.
#
# Usage (from the repository root):
#   powershell -ExecutionPolicy Bypass -File guide\open_all.ps1
#   powershell -ExecutionPolicy Bypass -File guide\open_all.ps1 -NoBrowser
#   powershell -ExecutionPolicy Bypass -File guide\open_all.ps1 -NoCode
#
# If VS Code ("code") is on PATH, the repo folder and all files open together
# as tabs, so the links in guide\rishith.md work. Otherwise each file opens in
# its default application. guide\index.html opens in the default browser unless
# -NoBrowser is given. Missing files are skipped and reported.

param(
    [switch]$NoBrowser,
    [switch]$NoCode
)

$root = Split-Path -Parent $PSScriptRoot

$relative = @(
    'guide/rishith.md',
    'guide/flowchart.md',
    'guide/README.md',
    'README.md',
    'DESIGN.md',
    'docs/SDLC.md',
    'backend/finreq/pipeline.py',
    'backend/finreq/llm.py',
    'backend/finreq/models.py',
    'backend/finreq/config.py',
    'backend/finreq/masking.py',
    'backend/finreq/retrieval.py',
    'backend/finreq/storage.py',
    'backend/finreq/sdlc.py',
    'backend/finreq/artifacts.py'
)

$files = @()
$missing = @()
foreach ($rel in $relative) {
    $full = Join-Path $root ($rel -replace '/', '\')
    if (Test-Path -LiteralPath $full -PathType Leaf) { $files += $full } else { $missing += $rel }
}

# Every agent module except the package marker.
$agentDir = Join-Path $root 'src\finreq\agents'
if (Test-Path -LiteralPath $agentDir) {
    foreach ($agent in (Get-ChildItem -LiteralPath $agentDir -Filter '*.py' | Where-Object { $_.Name -ne '__init__.py' })) {
        $files += $agent.FullName
    }
}

$rest = @(
    'backend/server.py',
    'backend/cli.py',
    'backend/scripts/gates.py',
    'backend/eval/evaluate.py',
    'frontend/src/App.tsx',
    'frontend/src/lib/api.ts',
    'frontend/src/index.css',
    'frontend/src/components/RunView.tsx',
    'frontend/src/components/InputPanel.tsx',
    'frontend/src/components/review/ReviewStep.tsx',
    'frontend/src/components/DeliveryStep.tsx',
    'frontend/src/components/ExportStep.tsx'
)
foreach ($rel in $rest) {
    $full = Join-Path $root ($rel -replace '/', '\')
    if (Test-Path -LiteralPath $full -PathType Leaf) { $files += $full } else { $missing += $rel }
}

$code = Get-Command code -ErrorAction SilentlyContinue
$opened = 0
if ($code -and -not $NoCode) {
    $mode = 'VS Code'
    & code $root @files
    $opened = $files.Count
} else {
    $mode = 'default applications'
    foreach ($f in $files) {
        Invoke-Item -LiteralPath $f
        $opened++
    }
}

if (-not $NoBrowser) {
    $html = Join-Path $root 'guide\index.html'
    if (Test-Path -LiteralPath $html -PathType Leaf) {
        Start-Process -FilePath $html
        $opened++
    } else {
        $missing += 'guide/index.html'
    }
}

Write-Host ''
Write-Host 'Prism project guide' -ForegroundColor Blue
Write-Host ("  Opened {0} item(s) via {1}" -f $opened, $mode) -ForegroundColor Cyan
if ($missing.Count -gt 0) {
    Write-Host ("  Skipped {0} missing file(s):" -f $missing.Count) -ForegroundColor Cyan
    foreach ($m in $missing) { Write-Host ("    " + $m) -ForegroundColor Cyan }
}
Write-Host ''
