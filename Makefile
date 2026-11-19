PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
PYTEST ?= $(PYTHON) -m pytest
IMAGE_TESTS = tests/test_image_cleanup_tool.py tests/test_image_edge_cases.py tests/test_image_processing.py
CHECK_FILES = backend/app.py backend/config.py backend/routes/api.py backend/routes/blog/__init__.py backend/routes/admin/__init__.py backend/routes/ai/__init__.py

.PHONY: run test test-unit test-integration test-e2e test-images check lint coverage clean-artifacts diag-api

run:
	$(PYTHON) backend/app.py

test:
	$(PYTEST) tests/ -v

# 只跑单元测试（排除 integration / e2e）
test-unit:
	$(PYTEST) tests/ -q -m "not integration and not e2e"

# 只跑集成测试（线程、异步、持久化队列等）
test-integration:
	$(PYTEST) tests/ -q -m "integration and not e2e"

# 浏览器端到端测试（需要本机 Chrome/Chromium；可用 E2E_CHROME_BIN 指定）
test-e2e:
	E2E=1 $(PYTEST) tests/e2e -v

test-images:
	$(PYTEST) -q $(IMAGE_TESTS)

# 静态检查：编译检查 + ruff
lint:
	$(PYTHON) -m compileall -q backend tests scripts
	$(PYTHON) -m ruff check backend tests scripts

check: lint
	$(PYTEST) tests/ -q

coverage:
	COVERAGE_FILE=/tmp/simple-blog.coverage $(PYTHON) -m pytest tests/ -q \
		--cov=backend --cov-branch --cov-report=term-missing --cov-report=html \
		--cov-fail-under=40

clean-artifacts:
	rm -rf .coverage .pytest_cache htmlcov
	find . -path './.git' -prune -o -name '__pycache__' -type d -prune -exec rm -rf {} +
	find . -path './.git' -prune -o -name '.DS_Store' -delete

diag-api:
	$(PYTHON) scripts/diagnostics/api_perf_check.py
