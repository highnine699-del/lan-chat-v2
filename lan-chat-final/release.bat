@echo off  
setlocal enabledelayedexpansion  
set /p VERSION=Enter version (e.g. v1.3):  
git add .  
git commit -m "auto-release: !VERSION!"  
git tag -s !VERSION! -m "Release !VERSION!"  
git push origin main  
git push origin !VERSION!  
echo DONE RELEASE !VERSION!  
pause  
