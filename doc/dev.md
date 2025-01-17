# Dev
```
poetry install
#poetry run lint
poetry run python dev.py lint
#poetry run test
poetry run python dev.py test
```

## Config
```
poetry config pypi-token.pypi YOUR_PYPI_TOKEN
```

## Publish
```
# Build
poetry build
poetry publish
```

Run a specific test file
```
poetry run pytest tests/test_lru.py -x
```