# ZenBot — Security-first AI agent bot
# Multi-stage build for minimal image size

# --- Build stage ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir hatchling

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Build wheel
RUN pip wheel --no-deps --wheel-dir /wheels .

# --- Runtime stage ---
FROM python:3.12-slim AS runtime

LABEL maintainer="ZenBot Team"
LABEL description="Security-first AI agent bot for messaging platforms"

# Security: create non-root user
RUN groupadd -r zenbot && useradd -r -g zenbot -d /home/zenbot -s /bin/false zenbot

# Install the wheel and dependencies
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

# Create necessary directories with proper ownership and permissions
RUN mkdir -p /home/zenbot/.zenbot/audit \
             /home/zenbot/.zenbot/plugins \
             /home/zenbot/.zenbot/memory \
             /home/zenbot/.zenbot/trust_store \
             /home/zenbot/.zenbot/logs && \
    chown -R zenbot:zenbot /home/zenbot && \
    chmod 700 /home/zenbot/.zenbot

# Switch to non-root user
USER zenbot
WORKDIR /home/zenbot

# Expose ports
EXPOSE 8080 8081 8082

# Healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')" || exit 1

# Default command
ENTRYPOINT ["zenbot"]
CMD ["run"]
