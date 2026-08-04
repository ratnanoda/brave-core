// Copyright (c) 2026 The Haly Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// you can obtain one at https://mozilla.org/MPL/2.0/.

import fs from 'node:fs/promises'
import path from 'node:path'

const SOURCE_BRAND = 'Brave'
const TARGET_BRAND = 'Haly'

const SKIPPED_DIRECTORIES = new Set([
  '.git',
  '.idea',
  '.vscode',
  'node_modules',
  'out',
  'third_party',
  'vendor',
])

const GRIT_EXTENSIONS = new Set(['.grd', '.grdp', '.xtb'])
const HTML_EXTENSIONS = new Set(['.htm', '.html'])

const VISIBLE_HTML_ATTRIBUTES = new Set([
  'alt',
  'aria-description',
  'aria-label',
  'placeholder',
  'title',
])

const VISIBLE_PLIST_KEYS = new Set([
  'CFBundleDisplayName',
  'CFBundleGetInfoString',
  'CFBundleName',
  'NSHumanReadableCopyright',
])

const VISIBLE_DESKTOP_KEYS = new Set([
  'Comment',
  'GenericName',
  'Name',
  'X-GNOME-FullName',
])

function replaceBrand(value) {
  return value
    .replace(/\bBrave\b/g, TARGET_BRAND)
    .replace(/\bBRAVE\b/g, TARGET_BRAND.toUpperCase())
}

function replaceTextOutsideTags(value) {
  return value
    .split(/(<[^>]*>)/g)
    .map((part) => (part.startsWith('<') ? part : replaceBrand(part)))
    .join('')
}

function transformTaggedText(source, tagNames) {
  let output = source
  for (const tagName of tagNames) {
    const expression = new RegExp(
      `<${tagName}\\b([^>]*)>([\\s\\S]*?)<\\/${tagName}>`,
      'g',
    )
    output = output.replace(expression, (_match, attributes, body) => {
      return `<${tagName}${attributes}>${replaceTextOutsideTags(body)}</${tagName}>`
    })
  }
  return output
}

function transformGrit(source) {
  return transformTaggedText(source, ['message', 'translation'])
}

function transformAndroidXml(source) {
  return transformTaggedText(source, ['string', 'item'])
}

function transformHtmlTag(tag) {
  return tag.replace(
    /\b([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*("(?:\\.|[^"])*"|'(?:\\.|[^'])*')/g,
    (match, attributeName, quotedValue) => {
      if (!VISIBLE_HTML_ATTRIBUTES.has(attributeName.toLowerCase())) {
        return match
      }
      const quote = quotedValue[0]
      const value = quotedValue.slice(1, -1)
      return `${attributeName}=${quote}${replaceBrand(value)}${quote}`
    },
  )
}

function transformHtml(source) {
  const ignoredElements = new Set(['code', 'pre', 'script', 'style'])
  const ignoredStack = []
  const tokens = source.match(/<!--[\s\S]*?-->|<![^>]*>|<[^>]+>|[^<]+/g) || []

  return tokens
    .map((token) => {
      if (!token.startsWith('<')) {
        return ignoredStack.length === 0 ? replaceBrand(token) : token
      }

      if (token.startsWith('<!--') || token.startsWith('<!')) {
        return token
      }

      const closingMatch = token.match(/^<\s*\/\s*([A-Za-z0-9:-]+)/)
      if (closingMatch) {
        const element = closingMatch[1].toLowerCase()
        if (ignoredStack.at(-1) === element) {
          ignoredStack.pop()
        }
        return token
      }

      const openingMatch = token.match(/^<\s*([A-Za-z0-9:-]+)/)
      if (openingMatch) {
        const element = openingMatch[1].toLowerCase()
        if (ignoredElements.has(element) && !/\/\s*>$/.test(token)) {
          ignoredStack.push(element)
        }
      }

      return transformHtmlTag(token)
    })
    .join('')
}

function transformAppleStrings(source) {
  return source.replace(
    /^(\s*"(?:\\.|[^"\\])*"\s*=\s*")((?:\\.|[^"\\])*)("\s*;.*)$/gm,
    (_match, prefix, value, suffix) => `${prefix}${replaceBrand(value)}${suffix}`,
  )
}

function transformPlist(source) {
  return source.replace(
    /(<key>\s*([^<]+?)\s*<\/key>\s*<string>)([\s\S]*?)(<\/string>)/g,
    (match, prefix, key, value, suffix) => {
      if (!VISIBLE_PLIST_KEYS.has(key.trim())) {
        return match
      }
      return `${prefix}${replaceBrand(value)}${suffix}`
    },
  )
}

function transformDesktopEntry(source) {
  return source.replace(
    /^([A-Za-z0-9-]+(?:\[[^\]]+\])?=)(.*)$/gm,
    (match, prefix, value) => {
      const key = prefix
        .slice(0, prefix.indexOf('='))
        .replace(/\[[^\]]+\]$/, '')
      if (!VISIBLE_DESKTOP_KEYS.has(key)) {
        return match
      }
      return `${prefix}${replaceBrand(value)}`
    },
  )
}

function transformWindowsResource(source) {
  let inStringTable = false
  return source
    .split(/(?<=\n)/)
    .map((line) => {
      if (/^\s*STRINGTABLE\b/.test(line)) {
        inStringTable = true
        return line
      }
      if (inStringTable && /^\s*END\b/.test(line)) {
        inStringTable = false
        return line
      }

      const visibleMetadata =
        /^\s*VALUE\s+"(?:FileDescription|LegalCopyright|ProductName)"\s*,/i.test(
          line,
        )
      const visibleControl =
        /^\s*(?:CAPTION|CTEXT|DEFPUSHBUTTON|GROUPBOX|LTEXT|PUSHBUTTON|RTEXT)\b/i.test(
          line,
        )
      if (!inStringTable && !visibleMetadata && !visibleControl) {
        return line
      }

      return line.replace(/"((?:""|[^"])*)"/g, (_match, value) => {
        return `"${replaceBrand(value)}"`
      })
    })
    .join('')
}

function isAndroidValuesXml(relativePath) {
  return /(?:^|\/)res\/values(?:-[^/]+)?\/[^/]+\.xml$/i.test(relativePath)
}

function transformResource(relativePath, source) {
  const extension = path.extname(relativePath).toLowerCase()

  if (GRIT_EXTENSIONS.has(extension)) {
    return transformGrit(source)
  }
  if (extension === '.xml' && isAndroidValuesXml(relativePath)) {
    return transformAndroidXml(source)
  }
  if (HTML_EXTENSIONS.has(extension)) {
    return transformHtml(source)
  }
  if (extension === '.strings') {
    return transformAppleStrings(source)
  }
  if (extension === '.plist') {
    return transformPlist(source)
  }
  if (extension === '.desktop') {
    return transformDesktopEntry(source)
  }
  if (extension === '.rc') {
    return transformWindowsResource(source)
  }

  return source
}

function isCandidate(relativePath) {
  const extension = path.extname(relativePath).toLowerCase()
  return (
    GRIT_EXTENSIONS.has(extension)
    || HTML_EXTENSIONS.has(extension)
    || extension === '.strings'
    || extension === '.plist'
    || extension === '.desktop'
    || extension === '.rc'
    || (extension === '.xml' && isAndroidValuesXml(relativePath))
  )
}

async function* walk(directory, rootDirectory) {
  const entries = await fs.readdir(directory, { withFileTypes: true })
  for (const entry of entries) {
    if (entry.isSymbolicLink()) {
      continue
    }
    if (entry.isDirectory() && SKIPPED_DIRECTORIES.has(entry.name)) {
      continue
    }

    const absolutePath = path.join(directory, entry.name)
    if (entry.isDirectory()) {
      yield* walk(absolutePath, rootDirectory)
      continue
    }
    if (entry.isFile()) {
      yield {
        absolutePath,
        relativePath: path
          .relative(rootDirectory, absolutePath)
          .split(path.sep)
          .join('/'),
      }
    }
  }
}

export async function applyHalyRebrand(
  rootDirectory,
  { check = false } = {},
) {
  const changedFiles = []

  for await (const file of walk(rootDirectory, rootDirectory)) {
    if (!isCandidate(file.relativePath)) {
      continue
    }

    const source = await fs.readFile(file.absolutePath, 'utf8')
    if (
      !source.includes(SOURCE_BRAND)
      && !source.includes(SOURCE_BRAND.toUpperCase())
    ) {
      continue
    }

    const transformed = transformResource(file.relativePath, source)
    if (transformed === source) {
      continue
    }

    changedFiles.push(file.relativePath)
    if (!check) {
      await fs.writeFile(file.absolutePath, transformed)
    }
  }

  const action = check ? 'would update' : 'updated'
  console.log(
    `[Haly rebrand] ${action} ${changedFiles.length} user-facing resource file(s).`,
  )
  return changedFiles
}
