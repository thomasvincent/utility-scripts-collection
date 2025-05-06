FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy source code
COPY . .

# Install the package
RUN pip install -e .

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

ENTRYPOINT ["python", "-m", "opsforge"]
CMD ["--help"]