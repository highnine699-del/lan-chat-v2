$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$pythonPath = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $pythonPath) {
    $pythonPath = 'python'
}

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\LAN Chat.lnk')
$shortcut.TargetPath = $pythonPath
$shortcut.Arguments = '"' + (Join-Path $scriptDir 'launcher.py') + '"'
$shortcut.WorkingDirectory = $scriptDir
$shortcut.IconLocation = 'C:\Windows\System32\shell32.dll,173'
$shortcut.Description = 'Start LAN Chat Server'
$shortcut.Save()
Write-Host 'Desktop shortcut "LAN Chat" created! Check your desktop.'
