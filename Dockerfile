# Use a lightweight official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1
# Default port for the application
ENV PORT=5000
# Directory where database or json files will be stored
ENV DATA_DIR=/data

# Create a system user and group to run the app securely as non-root
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /sbin/nologin appuser

# Set the working directory
WORKDIR /app

# Create the data directory for persistent volume storage and adjust permissions
RUN mkdir -p /data && \
    chown -R appuser:appgroup /data && \
    chmod 770 /data

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY server.py .
COPY static/ ./static/

# Change ownership of the app directory to appuser
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Expose the application port
EXPOSE 5000

# Mount the /data directory as a volume for persistence
VOLUME ["/data"]

# Run the application with gunicorn, binding to the configured PORT
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} server:app"]
