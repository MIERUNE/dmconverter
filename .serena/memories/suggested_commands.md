# Development Commands

## Environment Setup (macOS)
```bash
# Create virtual environment with QGIS Python
uv venv --python /Applications/QGIS.app/Contents/MacOS/bin/python3 --system-site-packages

# Activate virtual environment
source .venv/bin/activate
```

## Testing
```bash
# Run all tests with QGIS Python
PYTHONPATH=. /Applications/QGIS.app/Contents/MacOS/bin/python3 -m pytest

# Run specific test file
PYTHONPATH=. /Applications/QGIS.app/Contents/MacOS/bin/python3 -m pytest tests/unit/test_file_parser.py

# Run tests with verbose output
PYTHONPATH=. /Applications/QGIS.app/Contents/MacOS/bin/python3 -m pytest -v
```

## Code Quality
```bash
# Lint check
uv run ruff check .

# Lint with auto-fix
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check format without changes
uv run ruff format --check .
```

## Useful Git Commands
```bash
git status
git diff
git log --oneline -10
```

## Project-Specific Notes
- Tests require QGIS Python environment
- Sample DM files are in `tests/sample_data/`
- QGIS availability is checked at runtime via try/except
