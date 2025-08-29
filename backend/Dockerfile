
# Stage 1: Build stage - Install dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies if any are needed in the future
# For now, this just sets up the environment

# Copy only the requirements file to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# Stage 2: Final stage - Create the production image
FROM python:3.11-slim

WORKDIR /app

# Copy installed wheels and application code from the builder stage
COPY --from=builder /app/wheels /wheels
COPY . .

# Install the wheels in the final image
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Expose the port the app runs on
EXPOSE 8000

# Simple start: run the FastAPI app directly
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
