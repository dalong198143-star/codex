@echo off
REM Move pagefile from C to D (run as Administrator)
echo Current pagefile on C: 12GB, peak usage: 1.3GB
echo Moving to D: with 4096MB limit...
echo.

wmic pagefileset where name="C:\\pagefile.sys" delete
wmic pagefileset create name="D:\\pagefile.sys"
wmic pagefileset where name="D:\\pagefile.sys" set InitialSize=4096,MaximumSize=8192

echo.
echo Done! Reboot required.
echo Current config:
wmic pagefile list /format:list
pause
