// Copyright (c) 2026 The Haly Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// you can obtain one at https://mozilla.org/MPL/2.0/.

import fs from 'node:fs/promises'
import path from 'node:path'

const SKIPPED_DIRECTORIES = new Set([
  '.git',
  '.idea',
  '.vscode',
  'node_modules',
  'out',
  'third_party',
  'vendor',
])

const SOURCE_EXTENSIONS = new Set([
  '.cc',
  '.cpp',
  '.css',
  '.grd',
  '.grdp',
  '.h',
  '.hpp',
  '.htm',
  '.html',
  '.java',
  '.js',
  '.json',
  '.kt',
  '.m',
  '.md',
  '.mm',
  '.mjs',
  '.patch',
  '.plist',
  '.rc',
  '.strings',
  '.ts',
  '.tsx',
  '.txt',
  '.xml',
  '.xtb',
  '.yaml',
  '.yml',
])

function transformScheme(source) {
  return source
    .replaceAll('brave://', 'haly://')
    .replaceAll('BRAVE://', 'HALY://')
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
    if (!entry.isFile()) {
      continue
    }

    yield {
      absolutePath,
      relativePath: path
        .relative(rootDirectory, absolutePath)
        .split(path.sep)
        .join('/'),
    }
  }
}

export async function applyHalySchemeRebrand(
  rootDirectory,
  { check = false } = {},
) {
  const changedFiles = []

  for await (const file of walk(rootDirectory, rootDirectory)) {
    if (!SOURCE_EXTENSIONS.has(path.extname(file.relativePath).toLowerCase())) {
      continue
    }

    let source
    try {
      source = await fs.readFile(file.absolutePath, 'utf8')
    } catch {
      continue
    }

    if (!source.includes('brave://') && !source.includes('BRAVE://')) {
      continue
    }

    const transformed = transformScheme(source)
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
    `[Haly scheme] ${action} ${changedFiles.length} source file(s) from brave:// to haly://.`,
  )
  return changedFiles
}
