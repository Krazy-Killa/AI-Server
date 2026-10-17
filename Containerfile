FROM docker.io/library/python:3.13-slim-trixie@sha256:8fb4cfa1a2616d7b8e0c2175cc6ad68f5729c34ea8488c0b360d2934b7be9024

ENV HOME=/var/lib/ai-server \
    PYTHONPATH=/opt/ai-server/ai-backend \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/ai-server

COPY ai-backend/requirements-linux.lock /tmp/requirements-linux.lock
RUN python -m pip install \
    --disable-pip-version-check \
    --no-cache-dir \
    --requirement /tmp/requirements-linux.lock

RUN mkdir -p /opt/ai-server/www
COPY --chown=999:990 ai-backend/*.py /opt/ai-server/ai-backend/
COPY --chown=999:990 ai-backend/gpu/*.py /opt/ai-server/ai-backend/gpu/
COPY --chown=999:990 index.html /opt/ai-server/www/index.html
COPY --chown=999:990 css/ /opt/ai-server/www/css/
COPY --chown=999:990 js/ /opt/ai-server/www/js/

EXPOSE 8000 8001
USER 999:990
WORKDIR /opt/ai-server/ai-backend
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
