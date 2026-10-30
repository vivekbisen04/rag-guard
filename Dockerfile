FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c 'from fastembed import TextEmbedding; TextEmbedding(model_name="BAAI/bge-small-en-v1.5", cache_dir="/srv/model-cache")'
COPY . .
COPY --from=frontend-build /frontend/dist ./frontend/dist
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
