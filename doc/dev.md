# Setup
```bash
./dev init
poetry config pypi-token.pypi YOUR_PYPI_TOKEN
```

# Dev
```bash
./dev lint
./dev lint-no-edit
./dev test
./dev test tests/test_lru.py -x
./dev build
```

# Release
```bash
./dev release
```
