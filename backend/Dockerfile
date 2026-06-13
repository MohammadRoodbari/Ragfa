FROM docker.arvancloud.ir/python:3.10-slim


ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app


RUN useradd --create-home --shell /bin/bash appuser


COPY requirements.txt .
COPY backend/requirements-backend.txt .

RUN pip install --no-cache-dir -r requirements-backend.txt \
-i http://pypi.devneeds.ir/simple/ --trusted-host pypi.devneeds.ir

RUN pip install --no-cache-dir -r requirements.txt \
-i http://pypi.devneeds.ir/simple/ --trusted-host pypi.devneeds.ir

COPY backend/ ./backend/
COPY src/ ./src/
COPY config/ ./config/


RUN mkdir -p /tmp/rag_uploads && chown -R appuser:appuser /app /tmp/rag_uploads

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["gunicorn", "backend.app.main:app", \
"--worker-class", "uvicorn.workers.UvicornWorker", \
"--workers", "4", \
"--bind", "0.0.0.0:8000", \
"--timeout", "120", \
"--access-logfile", "-"]
