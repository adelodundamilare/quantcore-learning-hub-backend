FROM python:3.11-slim as builder

ARG ALLOWED_ORIGINS
ARG CAPROVER_GIT_COMMIT_SHA
ARG CLOUDINARY_API_KEY
ARG CLOUDINARY_API_SECRET
ARG CLOUDINARY_CLOUD_NAME
ARG DATABASE_HOST
ARG DATABASE_NAME
ARG DATABASE_PASSWORD
ARG DATABASE_PORT
ARG DATABASE_USER
ARG EMAILS_FROM_EMAIL
ARG EMAILS_FROM_NAME
ARG PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
ARG POLYGON_API_KEY
ARG SECRET_KEY
ARG SENDGRID_API_KEY
ARG STRIPE_SECRET_KEY
ARG STRIPE_WEBHOOK_SECRET
ARG VERIFICATION_CODE_EXPIRE_MINUTES

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc6-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim as production

ARG ALLOWED_ORIGINS
ARG CAPROVER_GIT_COMMIT_SHA
ARG CLOUDINARY_API_KEY
ARG CLOUDINARY_API_SECRET
ARG CLOUDINARY_CLOUD_NAME
ARG DATABASE_HOST
ARG DATABASE_NAME
ARG DATABASE_PASSWORD
ARG DATABASE_PORT
ARG DATABASE_USER
ARG EMAILS_FROM_EMAIL
ARG EMAILS_FROM_NAME
ARG PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
ARG POLYGON_API_KEY
ARG SECRET_KEY
ARG SENDGRID_API_KEY
ARG STRIPE_SECRET_KEY
ARG STRIPE_WEBHOOK_SECRET
ARG VERIFICATION_CODE_EXPIRE_MINUTES

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

RUN groupadd -r appuser && useradd -r -g appuser appuser

RUN mkdir -p /app && chown -R appuser:appuser /app
USER appuser
WORKDIR /app

COPY --chown=appuser:appuser . .

RUN mkdir -p /app/uploads /app/logs /app/temp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
