param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"
$venvPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment not found at $venvPython. Create it with: py -3 -m venv venv"
    exit 1
}

if ($Args.Count -eq 0) {
    & $venvPython manage.py help
    exit 0
}

if ($Args[0].ToLower() -eq "manage.py") {
    $cmdArgs = $Args[1..($Args.Count - 1)]
    & $venvPython manage.py @cmdArgs
}
else {
    & $venvPython manage.py @Args
}
