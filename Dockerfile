FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY orchestrator/ orchestrator/
RUN pip install --no-cache-dir .
COPY scripts/ scripts/

EXPOSE 8000

CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]
