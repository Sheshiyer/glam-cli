# GitHub Repo Setup: glam-cli

Use this when migrating from `gram-cli` to new repo `glam-cli`.

## 1. Create Repo

Create `twc-vault/glam-cli` on GitHub.

## 2. Point Local Git Remote

```bash
git remote rename origin old-origin || true
git remote add origin git@github.com:Sheshiyer/glam-cli.git
```

## 3. Push Main Branch

```bash
git push -u origin main
```

## 4. Push Tags

```bash
git push origin --tags
```

## 5. Release Baseline

```bash
git tag v0.2.0
git push origin v0.2.0
```

Then create GitHub Release `v0.2.0` and attach:

- `dist/glam_cli-0.2.0.tar.gz`
- `dist/glam_cli-0.2.0-py3-none-any.whl`

## 6. Post-Push Checks

- README links resolve to `twc-vault/glam-cli`.
- PyPI package name is `glam-cli`.
- npm package name is `glam-cli`.
- Homebrew formula path is `homebrew/glam-cli.rb`.
