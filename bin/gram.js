#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const currentDir = dirname(fileURLToPath(import.meta.url));
const glamPath = join(currentDir, 'glam.js');
const child = spawn(process.execPath, [glamPath, ...process.argv.slice(2)], { stdio: 'inherit' });

child.on('close', (code) => {
  process.exit(code ?? 0);
});

child.on('error', (error) => {
  console.error(`gram alias failed: ${error.message}`);
  process.exit(1);
});
