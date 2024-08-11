.PHONY: clean-venv
clean-venv:
	@python -c "import shutil; import pathlib; venv_path = pathlib.Path(shutil.which('poetry')).parent / '.venv'; shutil.rmtree(venv_path, ignore_errors=True)"
	poetry install

.PHONY: format
format: 
	@poetry run black .
	@poetry run isort .

.PHONY: lint
lint:
	@poetry run flake8 .

.PHONY: security
security:
	@poetry run bandit -c pyproject.toml -r .
	@poetry run pip-audit

.PHONY: test
test:
	@poetry run pytest

.PHONY: all
all: format lint security test

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  clean-venv        - Remove the virtual environment and reinstall dependencies"
	@echo "  format            - Run black and isort to format the code"
	@echo "  lint              - Run flake8 to lint the code"
	@echo "  security          - Run bandit and pip-audit for security checks"
	@echo "  test              - Run pytest to execute tests"
	@echo "  all               - Run format, lint, security, and test commands"
	@echo "  help              - Display this help message"

# Make 'all' the default target when no target is specified
.DEFAULT_GOAL := all
