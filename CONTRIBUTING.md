# Contributing to NuageVault

Thank you for taking the time to contribute! This guide explains how to work on this project correctly.

## Branching Strategy

Never commit directly to `main`. Always create a feature branch first.

### Step by Step

**1. Make sure you're on main and up to date:**
```bash
git checkout main
git pull origin main
```

**2. Create a new branch:**
```bash
git checkout -b feature/what-you-are-doing
```

**3. Make your changes, then commit:**
```bash
git add .
git commit -m "type(scope): short description"
```

**4. Push your branch to GitHub:**
```bash
git push origin feature/what-you-are-doing
```

**5. Go to GitHub → Create Pull Request → Merge into main**

**6. After merging, clean up:**
```bash
git checkout main
git pull origin main
git branch -d feature/what-you-are-doing
```

---

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description
```

### Types

| Type | When to use |
|---|---|
| `feat` | Adding a new feature |
| `fix` | Fixing a bug |
| `docs` | Changes to documentation only |
| `chore` | Cleanup, removing files, config changes |
| `refactor` | Restructuring code without changing behavior |
| `style` | Formatting, missing semicolons, etc |
| `test` | Adding or fixing tests |

### Examples

```bash
feat(auth): add email verification via Resend
fix(photos): correct S3 pre-signed URL expiry time
docs(readme): update IAM policy with least privilege
chore: remove stale SQLite and alembic files
refactor(auth): move token logic to tokens.py
```

### Rules
- Keep it under 50 characters
- Use present tense — "add feature" not "added feature"
- Be specific — "fix login bug" not "fix stuff"

---

## Branch Naming

```
feature/short-description     → new features
fix/short-description         → bug fixes
docs/short-description        → documentation only
chore/short-description       → cleanup tasks
```

### Examples
```
feature/add-dark-mode
fix/album-delete-bug
docs/update-readme
chore/remove-unused-files
```

---

## Environment Setup

See [README.md](README.md) for full setup instructions.

Quick summary:
- Backend: FastAPI running on Render
- Frontend: React + Vite running on Vercel
- Database: AWS DynamoDB
- Storage: AWS S3

Never commit `.env` files — use `.env.example` as a template.
