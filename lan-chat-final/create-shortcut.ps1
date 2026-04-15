$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\LAN Chat Server.lnk')
$shortcut.TargetPath = Join-Path $scriptDir 'start.bat'
$shortcut.WorkingDirectory = $scriptDir
$shortcut.IconLocation = 'C:\Windows\System32\cmd.exe,0'
$shortcut.Description = 'Start LAN Chat Server'
$shortcut.Save()
Write-Host 'Desktop shortcut created successfully!'
