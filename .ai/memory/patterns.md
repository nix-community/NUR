# Patterns

## Repo hygiene

- Seed zero-commit repos via Contents API PUT (blob endpoint 409s on
  zero-commit repos).
- Remove `__pycache__` before `git add -A`.
- `push_via_api.py` cannot push repos with no local parent commit.

## Repomap (codebase map for agents)

One-shot generation:

```
nix run github:qompassai/nix?dir=repomap -- /path/to/repo --budget 15000 --out .repomap.txt
```

`.repomap.txt` is a derived artifact — gitignore it, never commit it.
Currently Rust-only; other languages pending tree-sitter grammars.
