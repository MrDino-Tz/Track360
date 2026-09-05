# ---- Frontend build stage ----
FROM node:20-alpine AS frontend-build

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/public ./public
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src ./src
RUN npm run build

# ---- Runtime stage ----
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY --from=frontend-build /build/dist ./frontend/dist

RUN mkdir -p /app/data

ENV DATABASE_URL=sqlite:////app/data/plant.db
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]