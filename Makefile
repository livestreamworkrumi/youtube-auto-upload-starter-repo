.PHONY: install run run-demo test clean lint format

# Default target
all: install

# Install dependencies
install:
	pip install -r requirements.txt

# Run in demo mode
run-demo:
	DEMO_MODE=true python -m app.main

# Run in real mode
run:
	DEMO_MODE=false python -m app.main

# Run tests
test:
	pytest tests/ -v

# Run tests with coverage
test-coverage:
	pytest tests/ --cov=app --cov-report=html

# Clean up generated files
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf *.egg-info/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Lint code
lint:
	flake8 app/ tests/ --max-line-length=100
	mypy app/ --ignore-missing-imports

# Format code
format:
	black app/ tests/ --line-length=100

# Setup development environment
setup-dev: install
	python -m app.db
	python scripts/create_demo_db.py

# Run OAuth flow for YouTube
oauth:
	python scripts/run_oauth_flow.py

# Create sample database
demo-db:
	python scripts/create_demo_db.py
