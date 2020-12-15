# Contributing

## Making pull requests

Issues, feature requests and code contributions are welcomed. Follow these steps to make a pull request:

1. Fork/clone the repository.

1. Install dependencies (you'll probably want to create a virtual environment, using your preferred method, first).

   ```bash
   pip install poetry
   poetry install --extras "graylog"
   ```

1. Install pre-commit hooks

   ```bash
   pre-commit install
   ```

1. After making changes and having written tests, make sure tests pass:

   ```bash
   pytest
   ```

1. Commit, push, and make a PR.

## Version bumping

`loga` adheres to semantic versioning, ideally via the `bump2version` utility. Install it with pip:

```bash
pip install bump2version
```

Whenever you need to bump version, in the project root directory do:

```bash
bump2version (major | minor | patch)
git push <remote> <branch> --follow-tags 
```
