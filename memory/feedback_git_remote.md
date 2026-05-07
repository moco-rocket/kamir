---
name: Use fork remote for all git operations
description: Always push to and create PRs from the fork remote (moco-rocket/kamir), not origin (Pajdusakova/kamir)
type: feedback
---

Always use the `fork` remote (`https://github.com/moco-rocket/kamir.git`) for push, PR creation, and all write operations.

**Why:** The user is working on their fork of Kamir. `origin` points to the upstream repo (Pajdusakova/kamir) where the user does not have write access.

**How to apply:** Use `git push fork <branch>` and `gh pr create --repo moco-rocket/kamir` (or `--head moco-rocket/kamir:<branch>`) for all git operations in this repo.
