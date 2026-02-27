#!/usr/bin/env node

import { spawn } from 'node:child_process';

const python = process.env.PYTHON || process.env.PYTHON3 || 'python3';
const args = ['-m', 'gram', ...process.argv.slice(2)];

const child = spawn(python, args, { stdio: 'inherit' });

child.on('close', (code) => {
  process.exit(code ?? 0);
});

child.on('error', (error) => {
  console.error(`glam-cli: failed to start Python command (${python}): ${error.message}`);
  process.exit(1);
});
