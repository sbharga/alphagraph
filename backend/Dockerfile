FROM python:3.11-slim

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /project

# Copy dependency files first for layer caching
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Install production dependencies into backend/.venv
RUN cd backend && uv sync --frozen --no-dev

# Copy the rest of the backend source
COPY backend/ ./backend/

# Runtime directories (overridden by volumes in compose)
RUN mkdir -p .data artifacts

ENV PATH="/project/backend/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "alphagraph.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
