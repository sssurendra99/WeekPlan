.PHONY: help install dev-install test lint format flatpak-build flatpak-run flatpak-clean flatpak-sources clean run

help:
	@echo "WeekPlan — make targets"
	@echo "  make install         Install to user pip"
	@echo "  make dev-install     Install in editable mode with dev deps"
	@echo "  make run             Run the app from source"
	@echo "  make test            Run pytest"
	@echo "  make lint            Run ruff check + format check"
	@echo "  make format          Auto-format with ruff"
	@echo "  make flatpak-build   Build Flatpak from manifest and install --user"
	@echo "  make flatpak-run     Run the installed Flatpak"
	@echo "  make flatpak-clean   Remove build artifacts"
	@echo "  make flatpak-sources Regenerate Python deps for Flatpak"
	@echo "  make clean           Remove all build artifacts"

install:
	pip install --user .

dev-install:
	pip install -e ".[dev]"
	pre-commit install

run:
	python -m weekplan

test:
	pytest -v

lint:
	ruff format --check .
	ruff check .

format:
	ruff format .
	ruff check --fix .

flatpak-build:
	flatpak-builder --user --install --force-clean build-dir data/flatpak/com.weekplan.app.json

flatpak-run:
	flatpak run com.weekplan.app

flatpak-clean:
	rm -rf build-dir .flatpak-builder repo

flatpak-sources:
	bash scripts/generate-flatpak-sources.sh

clean: flatpak-clean
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build dist .pytest_cache .ruff_cache .coverage coverage.xml htmlcov
