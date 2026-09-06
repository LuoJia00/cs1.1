param(
    [string]$PythonVersion = "3.12.10"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot
$pythonDir = Join-Path $root "python"
$pythonExe = Join-Path $pythonDir "python.exe"
$stageRoot = Join-Path $root (".python-bootstrap-{0}" -f $PID)
$stagePython = Join-Path $stageRoot "python"

# These hashes pin the official files used to create the local runtime.
$pythonSha256 = "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"
$pipSha256 = "71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e"
$pythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$pipUrl = "https://files.pythonhosted.org/packages/f3/6e/1736e5b4ae2b778ef2f81c47d797de9f891d4d8acb047a24ca37a60294dd/pip-26.2.1-py3-none-any.whl"

function Get-CheckedDownload {
    param(
        [string]$Url,
        [string]$Destination,
        [string]$ExpectedSha256
    )

    Write-Host "Downloading $Url"
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Destination
    $actual = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $ExpectedSha256.ToLowerInvariant()) {
        throw "Downloaded file verification failed: $Destination"
    }
}

if (Test-Path -LiteralPath $pythonExe) {
    Write-Host "Bundled Python already exists: $pythonExe"
    exit 0
}

if (Test-Path -LiteralPath $pythonDir) {
    throw "The python folder exists but python.exe is missing. Rename or remove that incomplete folder, then try again: $pythonDir"
}

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    New-Item -ItemType Directory -Force -Path $stagePython | Out-Null

    $pythonZip = Join-Path $stageRoot "python.zip"
    $pipWheel = Join-Path $stageRoot "pip.whl"
    Get-CheckedDownload -Url $pythonUrl -Destination $pythonZip -ExpectedSha256 $pythonSha256
    Get-CheckedDownload -Url $pipUrl -Destination $pipWheel -ExpectedSha256 $pipSha256

    Write-Host "Preparing the project Python runtime..."
    Expand-Archive -LiteralPath $pythonZip -DestinationPath $stagePython -Force

    $pthFile = Get-ChildItem -LiteralPath $stagePython -Filter "python*._pth" -File | Select-Object -First 1
    if (-not $pthFile) {
        throw "Python path configuration file was not found in the downloaded package."
    }
    $pth = @(Get-Content -LiteralPath $pthFile.FullName)
    $hasSite = $false
    for ($i = 0; $i -lt $pth.Count; $i++) {
        if ($pth[$i] -match '^\s*#?\s*import site\s*$') {
            $pth[$i] = 'import site'
            $hasSite = $true
        }
    }
    if (-not $hasSite) {
        $pth += 'import site'
    }
    Set-Content -LiteralPath $pthFile.FullName -Value $pth -Encoding ASCII

    $sitePackages = Join-Path $stagePython "Lib\site-packages"
    New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
    $pipZip = Join-Path $stageRoot "pip.zip"
    Copy-Item -LiteralPath $pipWheel -Destination $pipZip
    Expand-Archive -LiteralPath $pipZip -DestinationPath $sitePackages -Force

    & (Join-Path $stagePython "python.exe") -m pip --version
    if ($LASTEXITCODE -ne 0) {
        throw "The downloaded Python runtime could not start pip."
    }

    Move-Item -LiteralPath $stagePython -Destination $pythonDir
    Write-Host "Python $PythonVersion is ready: $pythonExe"
} finally {
    if (Test-Path -LiteralPath $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
}
