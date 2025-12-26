FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Create a non-root user
RUN addgroup --system appgroup && adduser --system --group appuser

# Switch ownership of the application directory
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

# gcloud builds submit --tag gcr.io/YOUR_PROJECT/ingest-job

#gcloud run jobs create ingest-job \
#  --image gcr.io/YOUR_PROJECT/ingest-job \
#  --region us-central1 \
#  --vpc-connector YOUR_CONNECTOR_OR_DIRECT_VPC \
#  --set-env-vars DB_HOST=10.x.x.x,DB_PASSWORD=secret

# gcloud run jobs execute ingest-job