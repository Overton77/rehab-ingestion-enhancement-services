FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN pip install --no-cache-dir uv
COPY . /app
RUN uv sync --all-packages --frozen
CMD ["python", "-c", "print('override CMD per service in ECS task')"]
