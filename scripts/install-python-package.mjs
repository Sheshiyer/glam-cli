import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

if (process.env.GLAM_SKIP_PYTHON_INSTALL === '1') {
  process.exit(0);
}

const scriptDir = dirname(fileURLToPath(import.meta.url));
const packageJsonPath = join(scriptDir, '..', 'package.json');
const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf8'));
const version = packageJson.version;
const packageSpec = `glam-cli==${version}`;

const python = process.env.PYTHON || process.env.PYTHON3 || 'python3';
const installCommand = [
  '-m',
  'pip',
  'install',
  '--upgrade',
  '--disable-pip-version-check',
  packageSpec
];

const result = spawnSync(python, installCommand, {
  stdio: 'inherit'
});

if (result.status !== 0) {
  console.error('glam-cli: postinstall failed to install Python package.');
  console.error('Set GLAM_SKIP_PYTHON_INSTALL=1 to skip this step if you manage Python yourself.');
  process.exit(result.status ?? 1);
}
