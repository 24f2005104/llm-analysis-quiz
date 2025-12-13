# Base Playwright image with Python included
FROM mcr.microsoft.com/playwright:focal

# Set working directory
WORKDIR /app

# Copy requirements and install without caching
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Expose port
EXPOSE 10000

# Start FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
