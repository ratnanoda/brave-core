# Haly user-facing rebrand

This fork applies a conservative `Brave` → `Haly` replacement to user-facing
resource text after each source sync. It also converts the internal browser URL
scheme from `brave://` to `haly://` for source-built binaries.

## Automatic use

`npm run init` and `npm run sync` invoke both passes after patches and hooks
finish. The passes are idempotent, so running sync again is safe.

## Manual use

```sh
node ./build/commands/scripts/halyRebrand.js
```

To check whether a checkout still contains pending replacements without
changing files:

```sh
node ./build/commands/scripts/halyRebrand.js --check
```

The check command exits with a non-zero status when files would be changed.

## Covered display resources

The display pass changes only display-oriented parts of these formats:

- GRIT messages and translations (`.grd`, `.grdp`, `.xtb`)
- Android values XML strings and items
- HTML text plus `alt`, `aria-description`, `aria-label`, `placeholder`, and
  `title` attributes
- Apple `.strings` values
- selected display-name and copyright keys in property lists
- Linux desktop entry names and descriptions
- Windows string tables, dialog labels, and product metadata

Lowercase `brave`, source identifiers such as `BraveBrowser`, executable names,
preference keys, domains, and external URLs are intentionally left unchanged.

## Source-built `haly://` scheme

The source-build variant changes the value of the existing upstream
`kBraveUIScheme` symbols to `haly`, preserving the symbol names to minimize the
patch surface. The post-sync scheme pass also changes exact `brave://` URL
literals to `haly://` across first-party source and resource files. It does not
change `brave.com`, source identifiers, metrics names, or plain uses of the word
`brave`.

This means source-built Haly uses addresses such as:

- `haly://newtab/`
- `haly://settings/`
- `haly://version/`

## Isolated Windows installer

The stable repackaged Windows installer is built from the official,
Authenticode-verified Brave payload. It uses an independent launcher,
installation directory, process name, and profile:

- program files: `%LOCALAPPDATA%\Programs\Haly`
- browser profile: `%LOCALAPPDATA%\Haly\User Data`
- launcher: `Haly.exe`
- browser process image: `haly-browser.exe`
- unique Inno Setup AppId
- no Brave Update service, default-browser registration, or Brave registry keys

The repackaged installer deliberately preserves binary WebUI resources
byte-for-byte to avoid renderer bad-message failures. Because its browser binary
was not compiled from the Haly source changes, that stability package keeps the
upstream `brave://` scheme. A true `haly://` Windows binary must come from the
full source-build path.

## Limitations

Hard-coded visible product text inside programming-language string literals is
not changed automatically unless it is an exact internal-scheme URL. Remaining
visible occurrences should be handled as small reviewed patches after building
and inspecting Haly.

The display pass may change visible legal or attribution strings containing the
standalone word `Brave`. Review those changes before distributing binaries
publicly.
