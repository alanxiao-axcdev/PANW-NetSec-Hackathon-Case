.PHONY: help install dev test test-unit test-integration test-security test-performance check lint format typecheck clean run benchmark security-report

help: ## Show this help message
	@echo "Companion - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	python -m pip install --upgrade pip
	pip install -e .

dev: ## Install with development dependencies
	python -m pip install --upgrade pip
	pip install -e ".[dev]"

# Testing targets
test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest tests/ -k "not integration and not security and not performance"

test-integration: ## Run integration tests
	pytest tests/test_integration.py -v

test-security: ## Run security tests
	pytest tests/test_security* tests/test_pii* tests/test_prompt_injection* -v

test-performance: ## Run performance benchmarks
	pytest tests/test_*benchmark*.py -v
	pytest benchmarks/ --benchmark-only

# Code quality targets
check: lint typecheck ## Run all code quality checks

lint: ## Run ruff linter
	uv run ruff check .

format: ## Format code with ruff
	uv run ruff format .

typecheck: ## Run type checking with pyright
	uv run pyright

# Application targets
run: ## Run companion CLI
	python -m companion.cli

# Benchmarking targets  
benchmark: ## Generate comprehensive benchmark report
	python benchmarks/generate_report.py

benchmark-inference: ## Benchmark model inference only
	python benchmarks/inference_benchmark.py

benchmark-quantization: ## Compare original vs quantized model
	python benchmarks/quantization_benchmark.py

benchmark-security: ## Measure security overhead
	python benchmarks/security_overhead_benchmark.py

# Security targets
security-report: ## Generate security testing report
	python -m companion.security_research.adversarial_tester --report

audit: ## View security audit log
	companion audit --last 7d

# Utility targets
clean: ## Clean build artifacts and caches
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

clean-data: ## WARNING: Delete all user data (use for testing only)
	@echo "⚠️  This will delete ALL journal data!"
	@read -p "Are you sure? (yes/NO): " confirm && [ "$$confirm" = "yes" ] && rm -rf ~/.companion || echo "Cancelled"

# Model management
download-model: ## Pre-download Qwen model
	python -c "from transformers import AutoTokenizer, AutoModelForCausalLM; AutoTokenizer.from_pretrained('Qwen/Qwen2.5-1.5B'); AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-1.5B')"

quantize-model: ## Generate quantized model
	python -m companion.inference.optimizer --quantize

# Documentation
docs-serve: ## Serve documentation locally (if using mkdocs)
	@echo "Documentation available in docs/ directory"
	@echo "Open README.md or see docs/USER_GUIDE.md"

# Development helpers
watch-tests: ## Run tests on file changes
	pytest-watch

profile: ## Profile application performance
	python -m cProfile -o profile.stats -m companion.cli
	python -m pstats profile.stats

# CI/CD simulation
ci: clean dev check test ## Simulate CI pipeline locally
	@echo "✅ All CI checks passed!"
