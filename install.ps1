# One-step install. In PowerShell:
#   irm https://raw.githubusercontent.com/JupiterianSoul/Abiotic-Factor-Mod-Editor-MCP-server/main/install.ps1 | iex
# Set ABF_MCP_DIR to choose the folder. ABF_MCP_DOWNLOAD_ONLY=1 stops before install.py runs.

function Install-AbfModEditorMcp {
    $ErrorActionPreference = "Stop"
    $repo = "JupiterianSoul/Abiotic-Factor-Mod-Editor-MCP-server"
    $target = if ($env:ABF_MCP_DIR) { $env:ABF_MCP_DIR } else { Join-Path $env:USERPROFILE "abf-mod-editor-mcp" }

    $python = $null
    foreach ($candidate in @(@("py", "-3"), @("python"))) {
        if (-not (Get-Command $candidate[0] -ErrorAction SilentlyContinue)) { continue }
        $launcherArgs = @($candidate | Select-Object -Skip 1)
        & $candidate[0] @launcherArgs -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
    }
    if (-not $python -and (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "Python 3.9 or newer is needed. Installing it for this user with winget."
        winget install --exact --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
        if (Get-Command py -ErrorAction SilentlyContinue) {
            py -3 -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) { $python = @("py", "-3") }
        }
    }
    if (-not $python) {
        Write-Host "Python 3.9 or newer is needed. Install it from https://www.python.org/downloads/, tick 'Add python.exe to PATH', reopen PowerShell, and run this again."
        return
    }

    if (Test-Path -LiteralPath (Join-Path $target ".git")) {
        Write-Host "$target is a git clone, so it won't be overwritten. Update it with git pull."
    } else {
        Write-Host "Downloading to $target"
        $work = Join-Path ([IO.Path]::GetTempPath()) ("abf-mcp-" + [Guid]::NewGuid().ToString("N"))
        New-Item -ItemType Directory -Path $work | Out-Null
        try {
            $zip = Join-Path $work "source.zip"
            Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/$repo/archive/refs/heads/main.zip" -OutFile $zip
            Expand-Archive -LiteralPath $zip -DestinationPath $work
            $source = Get-ChildItem -LiteralPath $work -Directory | Select-Object -First 1
            New-Item -ItemType Directory -Force -Path $target | Out-Null
            Copy-Item -Path (Join-Path $source.FullName "*") -Destination $target -Recurse -Force
        } finally {
            Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    if ($env:ABF_MCP_DOWNLOAD_ONLY) {
        Write-Host "Downloaded. Skipping install.py because ABF_MCP_DOWNLOAD_ONLY is set."
        return
    }
    $launcherArgs = @($python | Select-Object -Skip 1)
    & $python[0] @launcherArgs (Join-Path $target "install.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "install.py failed. See the message above."
        return
    }
    Write-Host ""
    Write-Host "Done. Restart the Mod Editor, open a mod, then start a new session in your AI app."
    Write-Host "Try saying: make the Crafting Bench cost 1 duct tape, then test it."
}

Install-AbfModEditorMcp
