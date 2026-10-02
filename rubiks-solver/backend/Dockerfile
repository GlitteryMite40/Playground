# rubiks-solver/backend/Dockerfile
#
# Builds the FastAPI backend with the rubiks-cube-NxNxN-solver installed.
#
# The solver is Linux-oriented: it uses wget and gunzip to download lookup
# tables from S3 on first run, and it builds C extensions at install time.
# Python 3.11 is required because the solver pins setuptools==49.2.0, which
# is incompatible with Python 3.12+.
#
# Build:  docker build -t rubiks-backend .
# Run:    docker run -p 8000:8000 -v ~/.rubiks-cube-lookup-tables:/root/.rubiks-cube-lookup-tables rubiks-backend

FROM python:3.11-slim

# System dependencies: git (clone), wget + gzip (solver table downloads),
# gcc + python3-dev (C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        wget \
        gzip \
        gcc \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clone and install the solver with --no-build-isolation
# (required because the repo pins setuptools==49.2.0)
RUN git clone --depth 1 \
        https://github.com/dwalton76/rubiks-cube-NxNxN-solver \
        /tmp/rubiks-cube-NxNxN-solver \
    && pip install --no-cache-dir --no-build-isolation /tmp/rubiks-cube-NxNxN-solver \
    && rm -rf /tmp/rubiks-cube-NxNxN-solver

# Copy backend source
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
