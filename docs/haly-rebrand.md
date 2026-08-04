# Haly user-facing rebrand

This fork applies a conservative `Brave` → `Haly` replacement to user-facing
resource text after each source sync.

## Automatic use

`npm run init` and `npm run sync` invoke the rebrand pass after patches and
hooks finish. The pass is idempotent, so running sync again is safe.

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

## Covered resources

The pass changes only display-oriented parts of these formats:

- GRIT messages and translations (`.grd`, `.grdp`, `.xtb`)
- Android values XML strings and items
- HTML text plus `alt`, `aria-description`, `aria-label`, `placeholder`, and
  `title` attributes
- Apple `.strings` values
- selected display-name and copyright keys in property lists
- Linux desktop entry names and descriptions
- Windows string tables, dialog labels, and product metadata

Lowercase `brave`, source identifiers such as `BraveBrowser`, URLs, executable
names, preference keys, and protocol names are intentionally left unchanged.
Changing those would break compatibility with the upstream source and existing
profiles.

## Limitations

Hard-coded text inside JavaScript, TypeScript, C++, or other programming-language
string literals is not changed automatically because those literals can be
internal API values rather than UI copy. Such remaining visible occurrences
should be handled as small reviewed patches after building and inspecting Haly.

This pass changes visible legal and attribution strings containing the standalone
word `Brave`, including About-page text. Review those changes before distributing
binaries publicly.
