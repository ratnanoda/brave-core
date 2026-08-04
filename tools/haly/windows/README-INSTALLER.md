# Haly Windows installer

The distributable Windows package is built with Inno Setup. Resource rewriting, executable renaming, upstream signature validation, and internal-scheme patching happen in the Windows CI build before packaging. The resulting `HalySetup-x64.exe` is an offline installer and performs no PowerShell or resource conversion on the user's computer.

The CI job uses sparse checkout, so it does not download the multi-gigabyte Brave source tree merely to produce the package. Windows compiler inputs are resolved to absolute native paths before compilation.

Version 4 deliberately avoids blind `Brave` replacements inside WebUI JavaScript and HTML. Product-name replacement is restricted to locale data, while exact `brave://` URL literals are rewritten separately. Before an installer artifact is uploaded, the Windows job must successfully render a normal page, `haly://version/`, and `haly://newtab/` without `RESULT_CODE_KILLED_BAD_MESSAGE`.

Isolation boundaries:

- program directory: `%LOCALAPPDATA%\Programs\Haly`
- browser profile: `%LOCALAPPDATA%\Haly\User Data`
- launcher: `Haly.exe`
- browser process: `haly-browser.exe`
- internal browser scheme: `haly://`
- unique Inno Setup AppId: `{6B94C2EC-3443-4B23-9A36-2B8A1C751208}`
- no Brave Update service or Brave registry registration

The upstream Brave executable signature is checked before the rebrand. Length-preserving changes to PE resources and the URL scheme invalidate the upstream signature afterward; the generated Haly installer is unsigned.
