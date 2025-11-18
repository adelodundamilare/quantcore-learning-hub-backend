# Smoke Test Suite

Comprehensive smoke testing for all API endpoints following DRY principles.

## Quick Start

```bash
make smoke-test          # Run all smoke tests
make smoke-critical      # Run critical tests only  
make smoke-verbose       # Verbose output
```

## Test Structure

```
tests/
├── endpoints/           # Smoke tests by module
├── helpers/            # DRY utilities
├── smoke_runner.py     # Test orchestrator
├── conftest_smoke.py   # Smoke-specific fixtures
└── conftest.py         # Main test configuration
```

## Test Categories

**Critical**: auth, billing, trading, course, enrollment
**Administrative**: admin, role, permission, account  
**Supporting**: notification, report, rewards, stock_options, utility, webhooks

## Test Principles

- **Smoke tests only**: Basic reachability and 2xx status codes
- **DRY implementation**: Shared utilities and patterns
- **No comments**: Self-documenting code
- **Consolidated imports**: All imports at file top
- **Realistic data**: Use factories and proper test data

## Usage Examples

```python
# Individual module
pytest tests/endpoints/test_billing.py -v

# All endpoints  
pytest tests/endpoints/ -v

# With coverage
pytest tests/endpoints/ --cov=app
```