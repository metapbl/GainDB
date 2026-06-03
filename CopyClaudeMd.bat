@echo off
powershell -sta -command "Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Collections.Specialized.StringCollection; $f.Add('C:\Users\ggoyo_zhxlvdr\GaindB\CLAUDE.md'); [System.Windows.Forms.Clipboard]::SetFileDropList($f)"
