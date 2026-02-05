# Task Completion Checklist

When completing a development task, ensure the following steps are performed:

## 1. Code Quality Checks
```bash
# Lint check
uv run ruff check .

# Format check
uv run ruff format --check .
```

If issues found, fix them:
```bash
uv run ruff check --fix .
uv run ruff format .
```

## 2. Run Tests
```bash
# All tests
PYTHONPATH=. /Applications/QGIS.app/Contents/MacOS/bin/python3 -m pytest

# With verbose output
PYTHONPATH=. /Applications/QGIS.app/Contents/MacOS/bin/python3 -m pytest -v
```

## 3. Verify Changes
- [ ] All new functions have type hints
- [ ] No `any` or `unknown` types used
- [ ] dataclass(frozen=True) for new data structures
- [ ] Pure functions where possible
- [ ] Relative imports for internal modules
- [ ] QGIS imports wrapped in try/except if applicable

## 4. Documentation
- [ ] Update `.kiro/specs/` if specification changed
- [ ] No unnecessary documentation files created

## 5. Git Commit (if requested)
```bash
git add .
git commit -m "message"
```

Note: Do not commit unless explicitly requested by user.
