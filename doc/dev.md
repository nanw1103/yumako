# Setup
```bash
poetry install
poetry config pypi-token.pypi YOUR_PYPI_TOKEN
```

# Dev
```bash
#Lint
poetry run python dev.py lint

#Test
poetry run pytest

# Run single test file
poetry run pytest tests/test_lru.py -x

#Build
poetry build
```

# Release
```bash
poetry run python dev.py release
```