# From PoC to Production: Enterprise AI Platform with RAG and Guardrails

This repository contains a full-stack, secure AI platform deployed on Google Cloud via Terraform. It enables secure, RAG-based chat with enterprise-grade security and automated PII protection, accessible to public users via Firebase Authentication.

## Architecture Overview

![Google Cloud Architecture](images/Google_Cloud_Architecture.jpg)
*Figure 1: Google Cloud Platform Architecture*

![AWS Architecture](images/AWS_Architecture.jpg)
*Figure 2: Correspondent AWS Architecture*

The platform is composed of three main layers:

1.  **Frontend (UI):** A modern, high-concurrency **Next.js** application providing a real-time streaming chat interface. Accessible publicly via Global Load Balancer, secured by Firebase Authentication.
2.  **Backend Agent (Neural Core):** An asynchronous **FastAPI** service orchestrating the RAG pipeline, secured by internal-only networking and Firebase Token verification.
3.  **Infrastructure (Terraform):** Fully automated deployment using "Infrastructure as Code."

## Architecture Decisions & Rationale

### 1. Authentication: Firebase Authentication
I chose **Firebase Authentication** to provide a flexible "Public Door" for the application while maintaining security. For Corporate Wall via IAP, refer to merge #4.
*   **Broad Access:** Allows users to sign in with Google, Microsoft (Hotmail/Outlook), Email/Password, and other providers, making the platform accessible to external users, not just internal employees.
*   **Application-Level Security:** Authentication is handled by the application logic (Frontend & Backend) using the Firebase SDK, replacing the previous infrastructure-level IAP barrier.
*   **Session Management:** Firebase handles secure session management and token refreshing on the client side.

### 2. Communication: Asyncio vs. Pub/Sub
While Pub/Sub is excellent for decoupled, asynchronous background tasks, I utilize **Python's `asyncio`** within FastAPI for the chat interface.
*   **Real-Time Requirement:** Chat users expect immediate, streaming responses. Pub/Sub is a "fire-and-forget" mechanism designed for background processing, not for maintaining the open, bidirectional HTTP connections required for streaming LLM tokens to a user in real-time.
*   **Concurrency:** `asyncio` allows a single Cloud Run instance to handle thousands of concurrent waiting connections (e.g., waiting for Vertex AI to reply) without blocking, providing high throughput for chat without the architectural complexity of a message queue.

### 3. Event-Driven Ingestion: Cloud Functions
I moved the document ingestion logic from a manual script to a **Google Cloud Function** triggered by Cloud Storage events.
*   **Automation:** Uploading a PDF to the `data_bucket` automatically triggers the function to parse, chunk, embed, and upsert the document into the vector database.
*   **Efficiency:** This is a serverless, event-driven approach. Resources are only consumed when a file is uploaded, rather than having a long-running service waiting for input.
*   **Scalability:** Each file upload triggers a separate function instance, allowing parallel processing of mass uploads without blocking the main chat application.

## AI Engine & Knowledge Core: Memory & RAG Implementation

The Backend Agent is designed as a stateful, retrieval-augmented system that balances high-performance search with secure session management.

### 1. Short-Term Memory (Session Context)
*   **Storage:** Utilizes **Google Cloud Firestore** (Native Mode) for low-latency persistence of chat history.
*   **Implementation:** Leverages `FirestoreChatMessageHistory` within the LangChain framework.
*   **Security & Isolation:** Every session is cryptographically scoped to the authenticated user's email (`user_email:session_id`). This ensures strict multi-tenancy where users can never access or "leak" into another's conversation history (IDOR protection).
*   **Context Injection:** The system automatically retrieves the last $N$ messages and injects them into the `history` placeholder of the RAG prompt, enabling multi-turn, context-aware dialogue.

### 2. Long-Term Memory (Knowledge Base)
*   **Vector Database:** Powered by **PostgreSQL 15** (Cloud SQL) with the `vector` extension (`pgvector`).
*   **Retrieval Logic:** Employs semantic similarity search using `VertexAIEmbeddings` (`textembedding-gecko@003`). For every query, the engine retrieves the top **5 most relevant chunks** ($k=5$) to provide grounded context to the LLM.
*   **Semantic Caching:** Integrated with **Redis (Memorystore)** using a `RedisSemanticCache`. If a user asks a question semantically similar to a previously cached query (threshold: 0.05), the system returns the cached response instantly, bypassing the LLM to save cost and reduce latency.

### 3. RAG Specifications & Document Ingestion
*   **Ingestion Pipeline:** A specialized `ingest.py` script handles the transformation of raw data into "AI-ready" vectors.
*   **Smart Chunking:** Uses the `RecursiveCharacterTextSplitter` to maintain semantic integrity:
    *   **Chunk Size:** 1000 characters/tokens.
    *   **Chunk Overlap:** 200 characters (ensures no loss of context at the edges of chunks).
    *   **Separators:** Prioritizes splitting by double newlines (paragraphs), then single newlines, then spaces.
*   **Document Support:** Includes a `DirectoryLoader` with `PyPDFLoader` to automatically parse and index complex PDF structures.

## Security & Resilience: A Multi-Layered Defense

This platform implements a robust, multi-layered security strategy. The codebase and infrastructure have been hardened against the following threats:

### 1. Web & Application Security (OWASP Top 10)
-   **SQL Injection (SQLi) Protection:**
    -   **Infrastructure Level:** Google Cloud Armor is configured with pre-configured WAF rules (`sqli-v33-stable`) to filter malicious SQL patterns at the edge.
    -   **Application Level:** The backend uses **`asyncpg`** (via LangChain's `PGVector`), which strictly employs parameterized queries, ensuring user input is never executed as raw SQL.
-   **Cross-Site Scripting (XSS) Protection:**
    -   **Infrastructure Level:** Cloud Armor WAF rules (`xss-v33-stable`) detect and block malicious script injection attempts.
    -   **Framework Level:** Next.js (Frontend) automatically sanitizes and escapes content by default, and the backend returns structured JSON to prevent direct script rendering.
-   **Broken Access Control & IDOR (Insecure Direct Object Reference):**
    -   **Verified Identity (Firebase):** The frontend authenticates users via Firebase and passes a verified JWT (`X-Firebase-Token`) to the backend.
    -   **Session Isolation:** Chat histories are cryptographically scoped to the authenticated user's email (`user_email:session_id`), preventing IDOR attacks.

### 2. DDoS & Resource Abuse Protection
-   **Edge Protection:** Cloud Armor implements a global rate-limiting policy (500 requests/min per IP) and a "rate-based ban" to mitigate large-scale volumetric DDoS and brute-force attacks.
-   **Application Resilience:** The backend core utilizes `slowapi` to enforce granular rate limiting (5 requests/min per user) specifically for expensive LLM operations, protecting against cost-based denial-of-service and resource exhaustion.
-   **Input Validation:** Pydantic models in the backend enforce a strict 10,000-character limit on user messages to prevent memory-exhaustion attacks.

### 3. AI & LLM Specific Security (OWASP Top 10 for LLM)
-   **Prompt Injection Mitigation:** The RAG prompt template uses strict structural delimiters (`----------`) and prioritized system instructions to ensure the model adheres to its enterprise role and ignores adversarial overrides contained within documents or user queries.
-   **Sensitive Data Leakage (PII):** Google Cloud DLP (Data Loss Prevention) is integrated into the core pipeline with a **Regex Fast-Path** and **Asynchronous Threading**. This automatically detects and masks PII in real-time without blocking the main event loop, ensuring high performance while minimizing API costs.
-   **Knowledge Base Security:** Data is stored in a private Cloud SQL (PostgreSQL) instance reachable only via a Serverless VPC Access connector, ensuring the "Brain" of the AI is never exposed to the public internet.

### 4. Infrastructure & Secret Management
-   **Secret Hardening:** Passwords and API keys are managed via Google Secret Manager. Terraform `lifecycle` policies prevent accidental exposure of these secrets in state files.
-   **Neural Core Proxying (A2A Auth):** The Backend Agent is deployed with `INGRESS_TRAFFIC_INTERNAL_ONLY`. Communication is secured by a **Service-Side API Proxy** (`/api/chat`).
    -   **Service-to-Service OIDC:** The frontend generates short-lived OIDC ID tokens using the `google-auth-library` to authenticate itself to the backend infrastructure.
    -   **User Identity:** The frontend passes the Firebase ID token for application-level user verification.
-   **Secure Defaults:** `.gitignore` and `.dockerignore` are optimized to prevent the accidental leakage of `*.tfvars`, `.env`, or local credentials.

### 5. Operational Resilience & Observability
-   **Circuit Breaker (Frontend):** The Next.js frontend implements the **Circuit Breaker** pattern (via `opossum`) for all backend communications.
    *   **Behavior:** If the backend fails **50% of requests** (e.g., due to a database outage), the circuit will "OPEN" and immediately return a "Service Unavailable" error to the client without waiting for timeouts.
    *   **Recovery:** After **10 seconds**, it will "half-open" to test if the backend is back online.
-   **Transient Error Recovery (Backend):** The Neural Core uses **exponential backoff retries** (via `tenacity`) for external dependencies (Vertex AI, SQL, Redis).
    *   **Policy:** Automatically retries up to **3 times** with exponential backoff if it encounters transient errors like `GoogleAPICallError`, `ServiceUnavailable`, or network timeouts.
-   **Auto-Healing (Infrastructure):** The Backend Agent is configured with **Liveness and Startup Probes** in Cloud Run.
    *   **Startup Probe:** Prevents traffic from reaching a container until it is fully initialized (DB connected, models loaded).
    *   **Liveness Probe:** Continuously pings the `/health` endpoint. If the backend freezes or becomes unresponsive (e.g., deadlocks), Cloud Run automatically kills and restarts the container, resolving the issue without manual intervention.
-   **Distributed Tracing:** Full-stack observability is implemented using **OpenTelemetry**. Traces propagate from the Frontend to the Backend and deep into the LangChain execution (Embeddings -> Retrieval -> Generation), visible in **Google Cloud Trace** for precise bottleneck analysis.

## Enhanced Enterprise Architecture (Optimized)

This platform has been upgraded for production-scale performance, cost efficiency, and sub-second perceived latency:

### 1. Global Scalability & High Availability
- **Horizontal Autoscaling:** Both Frontend and Backend services are configured for automatic horizontal scaling in Cloud Run. They can scale from zero to hundreds of concurrent instances to handle massive traffic spikes.
- **Cold-Start Mitigation:** The Frontend service maintains a minimum of 1 warm instance (`min_instance_count = 1`), ensuring immediate responsiveness and eliminating "cold start" latency for users.
- **Cloud SQL Read Pool:** While currently using a single instance for cost efficiency, the architecture is ready for a dedicated Read Replica in Cloud SQL. This horizontally scales read capacity for the vector database, ensuring that heavy document retrieval and search operations do not bottleneck the primary write instance.

### 2. Latency & Performance Optimization
- **Asynchronous I/O (Neural Core):** The backend is built on **FastAPI** and uses **`asyncpg`** for non-blocking database connections. This allows a single instance to handle thousands of concurrent requests with minimal resource usage.
- **Server-Sent Events (SSE):** Real-time token streaming from the LLM (Gemini 3 Flash) directly to the Next.js UI provides sub-second "Time-To-First-Token," creating a highly responsive user experience.
- **Asynchronous Thread Pooling:** Expensive operations like PII de-identification via Google Cloud DLP are offloaded to asynchronous background threads, preventing them from blocking the main request-response cycle.

### 3. Cost Control & Efficiency
- **Gemini 3 Flash Integration:** Utilizes the high-efficiency Flash model (`gemini-3-flash-preview`) for a 10x reduction in token costs and significantly lower latency compared to larger models.
- **DLP Fast-Path Guardrails:** Implemented a high-performance regex-based "pre-check" for PII. This intelligently bypasses expensive Google Cloud DLP API calls for clean content, invoking the API only when potential PII patterns are detected.
- **Global CDN Caching:** Google Cloud CDN is enabled at the Load Balancer level to cache static assets and common frontend resources globally, reducing origin server load and improving page load times.

## Performance & Scaling Roadmap

The current infrastructure is designed for high efficiency and is benchmarked to handle approximately **2,500 users per hour** with the standard provisioned resources.

### How to Actually Reach 1,000,000 Users per Hour

To handle this load, you must change the architecture:

#### Solution A: Offload Vector Search (Recommended)
Use a specialized engine designed for high-throughput vector search.

*   **Use:** Google Vertex AI Vector Search (formerly Matching Engine).
*   **Why:** It is fully managed and designed to handle billions of vectors and thousands of QPS with <10ms latency.
*   **Architecture Change:**
    *   **Postgres:** Only stores Chat History and User Metadata (cheap writes).
    *   **Vertex AI:** Handles the 2,800 QPS vector load.

## Local Development & Configuration

### 1. Running the Backend Locally

```bash
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
# Export your variables
export PROJECT_ID="your-project"
export REGION="us-central1"
export DB_HOST="your_db_host_ip"
export DB_PASSWORD="your_db_password"
... etc
uvicorn main:app --host 0.0.0.0 --port 8080
```

### 2. Running the Frontend Locally

```bash
cd frontend-nextjs
npm install
npm audit fix --force
npm run dev
```

<img src="https://github.com/RubensZimbres/my-ai-platform/blob/development/images/frontend.png" width="600" />


## Ingestion Pipeline

The knowledge base is populated via an automated **Event-Driven Pipeline** using Google Cloud Functions.

1.  **Initialize Database:**
    Connect to your Cloud SQL instance (e.g., via Cloud Shell or a local client) and ensure the vector extension is enabled:
    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    ```

2.  **Upload Documents:**
    Upload your PDF documents to the **Data Bucket** created by Terraform (named `pdf-ingest-data-[suffix]`). You can do this via the Google Cloud Console or CLI:
    ```bash
    # Find your bucket name
    gsutil ls | grep pdf-ingest-data

    # Upload files
    gsutil cp local_docs/*.pdf gs://YOUR_DATA_BUCKET_NAME/
    ```

3.  **Automatic Processing:**
    The upload automatically triggers the **PDF Ingest Function**, which will:
    *   Parse the PDF text.
    *   Chunk the content (1000 tokens).
    *   Generate embeddings via Vertex AI.
    *   Upsert the vectors into the Cloud SQL database.

    You can view the logs in the Cloud Console under **Cloud Run Functions** -> `pdf-ingest-function` -> **Logs** to verify successful ingestion.

### Infrastructure (Terraform)
-   **Network (Zero-Trust):**
    -   **VPC Isolation:** A custom VPC with **Private Google Access**, ensuring all internal traffic stays within the Google network.
    -   **Private Service Access (PSA):** High-speed VPC Peering for Cloud SQL, Redis, and Vertex AI.
    -   **Cloud NAT:** Egress gateway allowing private backend instances to securely reach the internet for updates without exposing them to incoming public traffic.
-   **Compute & Identity:**
    -   **Dual-Agent Deployment:** Separate Cloud Run services for Frontend and Backend, each with its own **Least-Privilege Service Account**.
    -   **IAM Hardening:** Precise roles granted for Vertex AI (`roles/aiplatform.user`), Secret Manager (`roles/secretmanager.secretAccessor`), and Cloud SQL (`roles/cloudsql.client`).
-   **Governance & Cost Control:**
    -   **Automated Budgeting:** Proactive monthly budget alerts at 50%, 90%, and 100% of the target spend.
    -   **Anomaly Detection:** Cloud Monitoring policies that trigger email alerts if error rates spike or high-severity logs are detected.
-   **Edge Security (Ingress):**
    -   **Global Load Balancing:** HTTPS termination with **Managed SSL Certificates**.
    -   **Cloud Armor WAF:** Active protection against OWASP Top 10 (SQLi, XSS) and IP-based rate limiting (500 req/min).

## Component Details

### Frontend (Next.js Agent)
-   **Location:** `/frontend-nextjs`
-   **Tech:** React 18, Tailwind CSS, Lucide Icons, Firebase.
-   **Resilience:** **Circuit Breaker** (`opossum`) for fail-fast backend communication.
-   **Security:** Acts as a secure proxy to the Backend; Authentication handled via Firebase.
-   **Scalability:** Configured with `min_instances = 1` for zero-latency response.

### Backend (FastAPI Agent)
-   **Location:** `/backend-agent`
-   **Neural Core:** Orchestrates RAG using LangChain and Vertex AI.
-   **Resilience:** **Retries** (`tenacity`) for transient errors & **OpenTelemetry** tracing.
-   **Vector DB:** Cloud SQL for PostgreSQL 15 with `pgvector` and `asyncpg`.
-   **Networking:** Set to `INGRESS_TRAFFIC_INTERNAL_ONLY` to ensure it is unreachable from the public internet.

### Infrastructure (Terraform Modules)
-   **`network`**: VPC, Subnets, Cloud NAT, and PSA.
-   **`compute`**: Cloud Run services and granular IAM policies.
-   **`database`**: Cloud SQL (PostgreSQL) and Firestore (Chat History).
-   **`redis`**: Memorystore for semantic caching.
-   **`ingress`**: Global Load Balancer, Cloud Armor, and SSL.
-   **`billing_monitoring`**: Budgets, Alert Policies, and Notification Channels.

#### IAM Connectivity Matrix
The following table details the Zero-Trust permission model enforced by the infrastructure:

| Source | Target | Role | Status |
| :--- | :--- | :--- | :--- |
| Frontend SA | Backend Service | `roles/run.invoker` | ✅ Present |
| Backend SA | Vertex AI | `roles/aiplatform.user` | ✅ Present |
| Backend SA | Cloud SQL | `roles/cloudsql.client` | ✅ Present |
| Backend SA | Secret Manager | `roles/secretmanager.secretAccessor` | ✅ Present |
| Backend SA | Firestore | `roles/datastore.user` | ✅ Present |
| Backend SA | Cloud DLP | `roles/dlp.user` | ✅ Present |
| Function SA | Storage | `roles/storage.objectViewer` | ✅ Present |

## What To Do: A Deployment Guide for the AI Platform

Essential `gcloud` commands and manual steps required to successfully deploy the AI platform.

The steps are divided into two phases:
1.  **Pre-Terraform Setup:** Manual steps you must complete *before* running `terraform apply`.
2.  **Post-Terraform Actions:** Steps to take *after* your infrastructure is successfully provisioned.

---

## Phase 1: Pre-Terraform Setup (Manual Steps)

These actions prepare your Google Cloud project and grant the necessary permissions for Terraform and Cloud Build to run.

### 1.1. Initial Project and Billing Setup

First, log in and set up your project configuration.

```bash
# Log in to your Google Cloud account
gcloud auth login

# Set the project you will be working on
gcloud config set project [YOUR_PROJECT_ID]

# Link your project to a billing account (required to use most services)
gcloud beta billing projects link [YOUR_PROJECT_ID] --billing-account [YOUR_BILLING_ACCOUNT_ID]
```

### 1.2. Enable Required Google Cloud APIs

Terraform will require enablement of these resources.

```bash
# Enable all necessary APIs for the platform
gcloud services enable \
  compute.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  firestore.googleapis.com \
  serviceusage.googleapis.com \
  servicenetworking.googleapis.com \
  dlp.googleapis.com
```

### 1.3. Grant Permissions to the Cloud Build Service Account

The `cloudbuild-*.yaml` files build and deploy the applications. The default Cloud Build service account needs permission to do so.

```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")

# Grant Cloud Build permissions to deploy to Cloud Run and manage associated resources
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountAdmin"

# Grant Cloud Build permissions to push images to Artifact Registry
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

### 1.5. Grant Permissions to the Backend Service Account

The backend agent uses Google Cloud DLP for de-identifying PII. The backend service account needs permission to call the DLP API.

```bash
# Grant the Backend service account permission to use DLP
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:ai-backend-sa@$(gcloud config get-value project).iam.gserviceaccount.com" \
  --role="roles/dlp.user"
```

### 1.6. Configure Firebase Project (Manual UI Step)

Authentication is now handled by Firebase. This is a **manual, one-time setup**.

1.  **Go to Firebase Console:**
    *   Navigate to [console.firebase.google.com](https://console.firebase.google.com).
    *   Add a new project or select your existing Google Cloud project.
2.  **Enable Authentication:**
    *   Go to **Build -> Authentication**.
    *   Click **Get Started**.
    *   Go to **Sign-in method** tab.
    *   Enable **Email/Password**.
    *   Enable **Google**.
    *   Enable **Microsoft** (for Hotmail/Outlook users).
3.  **Register Web App:**
    *   Click the **Gear icon** (Project settings).
    *   Scroll to **Your apps**.
    *   Click the **</> (Web)** icon to register your app.
    *   Copy the `firebaseConfig` keys. You will need these for your local environment (`.env.local`) and your CI/CD pipeline.

---

## Phase 2: Post-Terraform Actions & Verification

After `terraform apply` completes successfully, perform these final steps to make the application fully functional.

### 2.1. Update DNS "A" Record

The Terraform `ingress` module provisioned a static IP for the load balancer. You must point your domain to it.

1.  **Get the Load Balancer IP Address:**
    ```bash
    terraform output public_ip
    ```
2.  **Update Your DNS:**
    *   Go to your domain registrar (e.g., Google Domains, Cloudflare, GoDaddy).
    *   Create or update the **"A" record** for the domain you specified in `terraform.tfvars` (e.g., `ai.your-company.com`).
    *   Point it to the IP address from the Terraform output.

**Note:** The managed SSL certificate and HTTPS routing will not work until your domain correctly resolves to the load balancer's IP address.

### 2.2. Enable `pgvector` Extension in Cloud SQL

The Terraform code correctly provisions the Cloud SQL instance with flags optimized for `pgvector`, but it cannot enable the extension itself.

1.  **Connect to the Cloud SQL instance:** Use your preferred PostgreSQL client (like `psql` or a GUI tool) to connect to the database using the IP address and the password stored in Secret Manager.
2.  **Run the SQL Command:** Execute the following command in your database to enable the vector extension.
    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    ```

### 2.3. Set the AI Provider API Key

The backend's Terraform configuration references a secret for the AI provider's API key. You must update the placeholder value with your real key.

```bash
# Add the first version of the secret with your actual API key
gcloud secrets versions add ai-provider-api-key --data-file="/path/to/your/api_key.txt"
```

### 2.4. Trigger Cloud Build to Deploy Your Code

Terraform has set up the infrastructure, but it uses a placeholder "hello world" container. You now need to run your Cloud Build pipelines to deploy your actual frontend and backend applications with the new resiliency features.

```bash
# Deploy the backend agent
gcloud builds submit --config cloudbuild-backend.yaml .

# Deploy the Next.js frontend
gcloud builds submit --config cloudbuild-frontend.yaml .
```
**Final step:** Replaces the placeholder services with your actual Next.js and FastAPI applications, making the platform live.

## Payment & Subscription System (New)

The platform now enforces a strict **"Login -> Pay -> Chat"** workflow using Stripe and Cloud SQL.

### 1. Payment Architecture
*   **Source of Truth:** The Cloud SQL (PostgreSQL) database is the single source of truth for user subscription status.
*   **Stripe Integration:**
    *   **Webhooks:** A secure `/webhook` endpoint listens for `checkout.session.completed` and `invoice.payment_succeeded` events from Stripe.
    *   **Automatic Activation:** When a payment succeeds, the webhook updates the user's `is_active` status in the `users` table.
*   **Security Enforcement:**
    *   **Backend Middleware:** The `get_current_user` dependency checks the database for every request. If `is_active` is false, it raises a `403 Forbidden` error.
    *   **Frontend Redirect:** The frontend intercepts these 403 errors and automatically redirects the user to the `/payment` page.

### 2. Database Schema
The new `users` table tracks subscription state:
*   `email` (Primary Key): Linked to Firebase Identity.
*   `is_active` (Boolean): Grants access to the chat.
*   `stripe_customer_id`: Links to the Stripe Customer.
*   `subscription_status`: Status string (e.g., 'active', 'past_due').

## Secrets Management (Required)

To deploy this platform securely, you must configure the following secrets in **Google Secret Manager**.

| Secret Name | Description | Required By |
| :--- | :--- | :--- |
| `PROJECT_ID` | Your Google Cloud Project ID. | Backend |
| `REGION` | GCP region (e.g., `us-central1`). | Backend, Ingest |
| `DB_HOST` | IP of your Cloud SQL instance (or `127.0.0.1` if using the Cloud SQL Auth Proxy). | Backend, Ingest |
| `DB_USER` | Database username (default: `postgres`). | Backend, Ingest |
| `DB_PASSWORD` | Password for the Cloud SQL (Postgres) 'postgres' user. | Backend, Terraform |
| `DB_NAME` | Name of the database (default: `postgres`). | Backend, Ingest |
| `DATABASE_URL` | Full SQLAlchemy connection string (e.g., `postgresql://user:pass@10.x.x.x/postgres`). | Backend |
| `REDIS_HOST` | Hostname/IP of the Redis instance. | Backend |
| `GOOGLE_API_KEY` | (Optional) API Key for Gemini/Vertex AI if not using ADC. | Backend |
| `STRIPE_API_KEY` | Stripe Secret Key (`sk_live_...`). | Backend |
| `STRIPE_WEBHOOK_SECRET` | Stripe Webhook Signing Secret (`whsec_...`). | Backend |
| `BACKEND_URL` | The internal URL of the backend (e.g. `http://localhost:8080`). Used by the server-side proxy. | Frontend |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase API Key. | Frontend |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase Auth Domain. | Frontend |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase Project ID. | Frontend |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | Firebase Storage Bucket. | Frontend |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Firebase Messaging Sender ID. | Frontend |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase App ID. | Frontend |

> **Note on Authentication:** The frontend uses Firebase. For local backend testing, you can use the `Bearer MOCK_TOKEN` header if `DEBUG=true` is set on the backend.
> **Note:** Frontend configuration variables (e.g., `NEXT_PUBLIC_FIREBASE_API_KEY`, `BACKEND_URL`) are not strictly "secrets" but should be managed via Cloud Run Environment Variables or build args.

**Acknowledgements**
✨ Google ML Developer Programs and Google Developers Program supported this work by providing Google Cloud Credits (and awesome tutorials for the Google Developer Experts)✨
