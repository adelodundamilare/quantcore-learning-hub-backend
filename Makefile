.PHONY: smoke-test smoke-critical smoke-verbose test-all clean-test

smoke-test:
	@echo "🔥 Running smoke tests..."
	@python tests/smoke_runner.py

smoke-critical:
	@echo "🔥 Running critical smoke tests..."
	@python tests/smoke_runner.py --critical

smoke-verbose:
	@echo "🔥 Running smoke tests (verbose)..."
	@python tests/smoke_runner.py --verbose

test-all:
	@echo "🧪 Running all tests..."
	@pytest tests/ -v

test-endpoints:
	@echo "🌐 Running endpoint tests..."
	@pytest tests/endpoints/ -v

clean-test:
	@echo "🧹 Cleaning test artifacts..."
	@rm -f test.db test_smoke.db
	@rm -rf .pytest_cache/
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true

lint-tests:
	@echo "🔍 Linting test files..."
	@flake8 tests/ --max-line-length=100
	@mypy tests/ --ignore-missing-imports

coverage-smoke:
	@echo "📊 Running smoke tests with coverage..."
	@pytest tests/endpoints/ --cov=app --cov-report=html --cov-report=term

help:
	@echo "Available commands:"
	@echo "  smoke-test      - Run all smoke tests"
	@echo "  smoke-critical  - Run critical smoke tests only"
	@echo "  smoke-verbose   - Run smoke tests with verbose output"
	@echo "  test-all        - Run all tests"
	@echo "  test-endpoints  - Run endpoint tests only"
	@echo "  clean-test      - Clean test artifacts"
	@echo "  lint-tests      - Lint test files"
	@echo "  coverage-smoke  - Run smoke tests with coverage"