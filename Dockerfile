FROM mcr.microsoft.com/playwright:v1.48.0-focal

WORKDIR /app

# Install pip properly
RUN python3 -m ensurepip --upgrade

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
