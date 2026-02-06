# FRED-SOL Makefile
# Common development tasks

.PHONY: install dev test lint format clean run demo help

# Installation
install:
	pip install -e .

dev:
	pip install -e ".[dev]"

full:
	pip install -e ".[full]"

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=. --cov-report=html --cov-report=term

test-fast:
	pytest tests/ -x -q

# Code Quality
lint:
	ruff check .

format:
	ruff format .

# Running
run:
	python cli.py run --dry-run

demo:
	python demo.py

monitor:
	python cli.py monitor --duration 60

dashboard:
	streamlit run streamlit_app.py

# Health Check
health:
	python health.py

# Cleaning
clean:
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

# Documentation
docs:
	@echo "Module Index:"
	@cat MODULE_INDEX.md

stats:
	@echo "=== FRED-SOL Stats ==="
	@echo "Python files:"
	@find . -name "*.py" ! -path "./.pytest_cache/*" | wc -l
	@echo "Total lines:"
	@find . -name "*.py" ! -path "./.pytest_cache/*" | xargs wc -l | tail -1
	@echo "Test files:"
	@find . -path "*/tests/*.py" | wc -l
	@echo "Commits:"
	@git log --oneline | wc -l

# Help
help:
	@echo "FRED-SOL Development Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install    Install package"
	@echo "  make dev        Install with dev dependencies"
	@echo "  make full       Install with all optional deps"
	@echo ""
	@echo "Testing:"
	@echo "  make test       Run all tests"
	@echo "  make test-cov   Run tests with coverage"
	@echo "  make test-fast  Run tests, stop on first failure"
	@echo ""
	@echo "Running:"
	@echo "  make run        Start agent in dry-run mode"
	@echo "  make demo       Run quick demo"
	@echo "  make monitor    Start live monitor (60s)"
	@echo "  make dashboard  Start Streamlit dashboard"
	@echo ""
	@echo "Other:"
	@echo "  make health     Run health check"
	@echo "  make stats      Show project stats"
	@echo "  make clean      Remove build artifacts"
