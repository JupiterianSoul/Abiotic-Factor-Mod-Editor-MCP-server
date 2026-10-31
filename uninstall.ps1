# Removes what install.ps1 added. Mod projects are not touched.
$ErrorActionPreference = "Continue"

if (Get-Command abiotic-mcp -ErrorAction SilentlyContinue) {
    abiotic-mcp uninstall
}
if (Get-Command claude -ErrorAction SilentlyContinue) {
    claude mcp remove abiotic 2>$null
}
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv tool uninstall abiotic-mcp 2>$null
}
if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m pip uninstall -y abiotic-mcp 2>$null
}
