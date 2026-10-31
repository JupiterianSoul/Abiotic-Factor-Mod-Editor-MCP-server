# Installs abiotic-mcp for the current user. No admin rights needed.
$ErrorActionPreference = "Stop"
$source = "git+https://github.com/JupiterianSoul/Abiotic-Factor-Mod-Editor-MCP-server"

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv tool install --force $source
    uv tool update-shell
    $exe = Join-Path (uv tool dir --bin) "abiotic-mcp.exe"
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Error "Python 3.10+ or uv is required. Get uv from https://docs.astral.sh/uv/"
    }
    & python -c "import sys; sys.exit(sys.version_info < (3, 10))"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Python 3.10 or newer is required. Get uv from https://docs.astral.sh/uv/"
    }
    & python -m pip install --user --upgrade $source
    $scripts = & python -c "import site, os; print(os.path.join(os.path.dirname(site.getusersitepackages()), 'Scripts'))"
    $exe = Join-Path $scripts "abiotic-mcp.exe"
}

& $exe install
& $exe doctor
