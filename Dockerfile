FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY nerm-mcp-server /app/nerm-mcp-server

RUN python -m pip install --upgrade pip && \
    python -m pip install -e /app/nerm-mcp-server

WORKDIR /app/nerm-mcp-server

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "from nerm.health import get_health_report; import sys; sys.exit(0 if get_health_report().get('status') == 'ok' else 1)"

CMD ["python", "-m", "main"]
