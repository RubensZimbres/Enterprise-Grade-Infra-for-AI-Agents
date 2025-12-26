FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Expose the port Streamlit will run on
EXPOSE 8080

# Create a non-root user
RUN addgroup --system appgroup && adduser --system --group appuser

# Switch ownership of the application directory
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Run Streamlit on port 8080 to satisfy Cloud Run requirements
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
