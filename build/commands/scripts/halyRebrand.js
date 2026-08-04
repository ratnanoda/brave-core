// Copyright (c) 2026 The Haly Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// you can obtain one at https://mozilla.org/MPL/2.0/.

import config from '../lib/config.ts'
import { applyHalyRebrand } from '../lib/halyRebrand.js'

const check = process.argv.includes('--check')
const changedFiles = await applyHalyRebrand(config.braveCoreDir, { check })

if (check && changedFiles.length > 0) {
  process.exitCode = 1
}
