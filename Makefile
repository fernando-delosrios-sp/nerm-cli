.PHONY: conformance-check
.PHONY: full-check
.PHONY: docker-build
.PHONY: docker-health
.PHONY: release-readiness
.PHONY: post-deploy-check
.PHONY: phase3-readiness

conformance-check:
	. .venv/bin/activate && \
	python -m pytest nerm-mcp-server/tests/unit/test_tool_endpoint_matrix_sync.py -q && \
	python -m pytest nerm-mcp-server/tests/unit/test_http_contracts.py -q && \
	python -m pytest nerm-mcp-server/tests/unit/test_http_client_resilience.py -q && \
	python -m pytest nerm-mcp-server/tests/unit/test_server_bootstrap.py -q && \
	python -m pytest nerm-mcp-server/tests/integration/test_real_tenant_smoke.py -q -rs

full-check:
	. .venv/bin/activate && \
	python -m pytest -q

docker-build:
	docker build -t nerm-agent:local .

docker-health:
	. .venv/bin/activate && \
	python -c "from nerm.health import get_health_report; import json; print(json.dumps(get_health_report(), indent=2))"

release-readiness:
	. .venv/bin/activate && \
	python -m pytest nerm-mcp-server/tests/unit/test_server_health.py -q && \
	python -m pytest nerm-mcp-server/tests/unit/test_http_client_resilience.py -q && \
	$(MAKE) conformance-check && \
	$(MAKE) full-check

post-deploy-check:
	. .venv/bin/activate && \
	python nerm-mcp-server/scripts/post_deploy_check.py

phase3-readiness:
	$(MAKE) release-readiness && \
	$(MAKE) post-deploy-check
