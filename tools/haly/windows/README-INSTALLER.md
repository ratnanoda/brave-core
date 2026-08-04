# Haly Windows installer

The distributable Windows package is built with Inno Setup. Resource-pack rewriting, executable renaming, and signature validation happen in the Windows CI build before packaging. The resulting `HalySetup-x64.exe` is an offline installer and performs no PowerShell or resource conversion on the user's computer.

Isolation boundaries:

- program directory: `%LOCALAPPDATA%\Programs\Haly`
- browser profile: `%LOCALAPPDATA%\Haly\User Data`
- launcher: `Haly.exe`
- browser process: `haly-browser.exe`
- unique Inno Setup AppId: `{6B94C2EC-3443-4B23-9A36-2B8A1C751208}`
- no Brave Update service or Brave registry registration
