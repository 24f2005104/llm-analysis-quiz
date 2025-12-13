# Use official Playwright image (includes Chromium + dependencies)
FROM mcr.microsoft.com/playwright:focal

# Set working directory
WORKDIR /app

# Copy requirements and install using python3 -m pip
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port 10000
EXPOSE 10000

# Run FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
