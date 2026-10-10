# G9 isolated on-prem engineering deployment image. Human acceptance remains OPEN.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /opt/mcias
COPY pyproject.toml /opt/mcias/pyproject.toml
COPY mcias/ /opt/mcias/mcias/
RUN python -m pip install --no-cache-dir /opt/mcias \
    && groupadd --system --gid 1900 mcias \
    && useradd --system --uid 1900 --gid 1900 --home-dir /nonexistent --shell /usr/sbin/nologin mcias
USER 1900:1900
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:8000/health/live', timeout=3).status == 200"
CMD ["uvicorn", "mcias.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
