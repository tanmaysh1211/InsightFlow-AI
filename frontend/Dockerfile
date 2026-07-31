FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose Streamlit standard port
EXPOSE 8501

# Run development server in container
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
