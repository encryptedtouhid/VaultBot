# VaultBot — Security-first AI agent bot
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

LABEL maintainer="VaultBot Team"
LABEL description="Security-first AI agent bot for messaging platforms"

# Security: create non-root user
RUN groupadd -r vaultbot && useradd -r -g vaultbot -d /home/vaultbot -s /bin/false vaultbot

# Install the wheel and dependencies
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

# Create necessary directories with proper ownership and permissions
RUN mkdir -p /home/vaultbot/.vaultbot/audit \
             /home/vaultbot/.vaultbot/plugins \
             /home/vaultbot/.vaultbot/memory \
             /home/vaultbot/.vaultbot/trust_store \
             /home/vaultbot/.vaultbot/logs && \
    chown -R vaultbot:vaultbot /home/vaultbot && \
    chmod 700 /home/vaultbot/.vaultbot

# Switch to non-root user
USER vaultbot
WORKDIR /home/vaultbot

# Expose ports
EXPOSE 8080 8081 8082

# Healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')" || exit 1

# Default command
ENTRYPOINT ["vaultbot"]
CMD ["run"]
