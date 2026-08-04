# Haly Windows installer

The distributable Windows package is built with Inno Setup. Executable renaming, upstream signature validation, and localization-only branding happen in the Windows CI build before packaging. The resulting `HalySetup-x64.exe` is an offline installer and performs no PowerShell or resource conversion on the user's computer.

The CI job uses sparse checkout, so it does not download the multi-gigabyte Brave source tree merely to produce the package. Windows compiler inputs are resolved to absolute native paths before compilation.

Stable version 5 fixes the New Tab crash by preserving binary WebUI resources byte-for-byte. The build refuses to continue if `brave_resources.pak`, `resources.pak`, `chrome_100_percent.pak`, or `chrome_200_percent.pak` differs from the verified upstream payload. Product-name replacement is restricted to locale packs and extension `_locales/messages.json` files.

Before an installer artifact is uploaded, the Windows job starts the browser with a private profile, connects through the Chrome DevTools Protocol, reads the live DOM, checks for bad-message and sad-tab errors, and captures screenshots of a normal renderer page, `brave://version/`, and `brave://newtab/`.

Isolation boundaries:

- program directory: `%LOCALAPPDATA%\Programs\Haly`
- browser profile: `%LOCALAPPDATA%\Haly\User Data`
- launcher: `Haly.exe`
- browser process: `haly-browser.exe`
- unique Inno Setup AppId: `{6B94C2EC-3443-4B23-9A36-2B8A1C751208}`
- no Brave Update service or Brave registry registration

The stable prebuilt-binary package keeps the upstream `brave://` internal scheme. A true `haly://` scheme changes scheme registration inside Chromium/Brave and therefore belongs to the source-build variant rather than the binary repackaging path.
