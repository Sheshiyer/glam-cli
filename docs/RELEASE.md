# glam-cli Release Guide

This checklist covers Python package, npm wrapper, Homebrew formula, and GitHub release.

## 1. Preflight

- Ensure repo is named `glam-cli` on GitHub.
- Ensure these versions match:
  - `pyproject.toml` -> `[project].version`
  - `src/gram/__init__.py` -> `__version__`
  - `package.json` -> `version`

## 2. Verify Quality Gates

```bash
ruff check src tests
mypy src
pytest
```

## 3. Build Python Artifacts

```bash
rm -rf dist
python3 -m build
python3 -m twine check dist/*
```

## 4. Publish Python Package

```bash
python3 -m twine upload dist/*
```

## 5. Publish npm Package

```bash
npm publish --access public
```

## 6. Update Homebrew Formula

1. Update formula url + sha from PyPI after publish:

```bash
python3 scripts/update-homebrew-from-pypi.py glam-cli <VERSION>
```

2. If needed (before PyPI publish), compute sha of the local sdist:

```bash
shasum -a 256 dist/glam_cli-<VERSION>.tar.gz
```

3. Update `homebrew/glam-cli.rb`:
- `url`
- `sha256`
- any dependency resource checksums (if version changes)

4. Validate formula syntax locally:

```bash
brew style homebrew/glam-cli.rb
```

5. After formula is in your tap, run:

```bash
brew audit --strict --tap twc-vault/glam glam-cli
brew install --build-from-source twc-vault/glam/glam-cli
brew test glam-cli
```

## 7. Commit, Tag, Push

```bash
git add .
git commit -m "release: v<VERSION>"
git tag v<VERSION>
git push origin main --tags
```

## 8. GitHub Release

- Create release `v<VERSION>`.
- Attach `dist/glam_cli-<VERSION>.tar.gz` and `dist/glam_cli-<VERSION>-py3-none-any.whl`.
- Verify release notes include major changes and migration notes (`gram` alias compatibility).

## 9. Post-Release Smoke

```bash
pip install --upgrade glam-cli
npm install -g glam-cli

glam --version
glam --help
```

## Notes

- `gram` remains an alias for backward compatibility.
- `glam` is the primary command and should be used in docs/examples.
