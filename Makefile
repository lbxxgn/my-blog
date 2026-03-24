PYTHON ?= python3
PYTEST ?= COVERAGE_FILE=/tmp/simple-blog.coverage pytest
IMAGE_TESTS = tests/test_image_cleanup_tool.py tests/test_image_edge_cases.py tests/test_image_processing.py
CHECK_FILES = backend/app.py backend/config.py backend/routes/blog.py backend/routes/api.py backend/utils/asset_optimizer.py build.py

.PHONY: run test test-images build-assets check clean-artifacts diag-api diag-assets diag-asset-optimizer

run:
	$(PYTHON) backend/app.py

test:
	$(PYTEST) tests/ -v

test-images:
	$(PYTEST) -q $(IMAGE_TESTS)

build-assets:
	$(PYTHON) build.py --merge --minify

check:
	$(PYTHON) -m py_compile $(CHECK_FILES)
	$(MAKE) test-images

clean-artifacts:
	rm -rf .coverage .pytest_cache htmlcov
	find . -path './.git' -prune -o -name '__pycache__' -type d -prune -exec rm -rf {} +
	find . -path './.git' -prune -o -name '.DS_Store' -delete

diag-api:
	$(PYTHON) scripts/diagnostics/api_perf_check.py

diag-assets:
	$(PYTHON) scripts/diagnostics/assets_perf_check.py

diag-asset-optimizer:
	$(PYTHON) scripts/diagnostics/asset_optimizer_check.py
