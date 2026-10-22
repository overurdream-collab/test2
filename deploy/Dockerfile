# G9 isolated on-prem engineering deployment image. Human acceptance remains OPEN.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /opt/mcias
COPY pyproject.toml /opt/mcias/pyproject.toml
COPY mcias/ /opt/mcias/mcias/
COPY alembic.ini /opt/mcias/alembic.ini
COPY alembic/ /opt/mcias/alembic/
# The optional test extra is used only by the local synthetic verifier.
ARG MCIAS_INSTALL_EXTRA=runtime
RUN --mount=type=secret,id=managed_ca \
    if [ -f /run/secrets/managed_ca ]; then export PIP_CERT=/run/secrets/managed_ca; fi; \
    case "$MCIAS_INSTALL_EXTRA" in \
      runtime) python -m pip install --no-cache-dir /opt/mcias ;; \
      verification) python -m pip install --no-cache-dir '/opt/mcias[test]' ;; \
      *) exit 1 ;; \
    esac \
    && groupadd --system --gid 1900 mcias \
    && useradd --system --uid 1900 --gid 1900 --home-dir /nonexistent --shell /usr/sbin/nologin mcias \
    && mkdir -p /var/lib/mcias /opt/mcias/.e2e-output \
    && chown 1900:1900 /var/lib/mcias /opt/mcias/.e2e-output
# Build-context permissions can be private on the packaging host. Make only
# first-party code/migrations readable to the existing non-root runtime user.
RUN chmod -R a+rX /opt/mcias/pyproject.toml /opt/mcias/alembic.ini /opt/mcias/alembic /opt/mcias/mcias
COPY --chmod=0644 scripts/check_integrated_workflow.py /opt/mcias/scripts/check_integrated_workflow.py
RUN chmod -R a+rX /opt/mcias/scripts
USER 1900:1900
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:8000/health/live', timeout=3).status == 200"
CMD ["uvicorn", "mcias.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
