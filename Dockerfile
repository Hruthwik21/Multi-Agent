FROM python:3.11-slim
WORKDIR /app
RUN useradd -m app && chown app:app /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY backend/ backend/
COPY frontend/ frontend/
COPY eval/ eval/
USER app
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
