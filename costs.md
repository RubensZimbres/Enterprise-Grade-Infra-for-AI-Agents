### **Executive Summary: Is there a fixed fee?**

**No, there is no $1,000/month subscription** (like a flat enterprise contract) in this plan. However, **this is NOT purely "pay-as-you-go" either.**

You are deploying several resources that run **24/7**, meaning you will be charged for every hour they exist, regardless of whether anyone uses your application.
**Estimated Fixed Monthly "Floor" Cost:** **~$180 - $220 USD per month** (assuming `us-central1`).
*This cost accumulates even if you have 0 users.*

---

### **Detailed Breakdown by Module**

#### **1. Module: `billing_monitoring**`

* **What is deployed:**
* **Budget:** A budget alert for $100 (alerts you at 50%, 90%, 100%).
* **Monitoring:** Custom metric for error counts and an alert policy for high error rates.
* **Notification:** Email channel.


* **Cost:** **~$0.00 / month**.
* Google Cloud Budgets and standard Alerting are generally free.
* Custom metrics can incur costs if you send millions of data points, but for this scale, it's negligible.



#### **2. Module: `cicd**`

* **What is deployed:**
* **Artifact Registry:** A Docker repository (`cloud-run-source-deploy`).
* **Cloud Build:** 2 Triggers (Frontend & Backend) connected to GitHub.


* **Cost:** **Pay-as-you-go (Low)**.
* **Builds:** You get 120 free build-minutes/day. Unless you commit code constantly, this is likely free.
* **Storage:** Artifact Registry charges ~$0.020 per GB/month for storing your Docker images.



#### **3. Module: `compute**` (Significant Cost)

* **What is deployed:**
* **Cloud Run Job:** `ingest-job` (Runs only when triggered).
* **Cloud Run Service:** `backend-agent` (2 vCPU, 4GB RAM).
* **Cloud Run Service:** `frontend-agent` (1 vCPU, 2GB RAM).


* **The "Hidden" Cost:**
* Both services have `min_instance_count = 1`. This keeps one copy of your app alive 24/7.
* **Backend Cost:** ~$40/month (Idle pricing for 2vCPU/4GB).
* **Frontend Cost:** ~$20/month (Idle pricing for 1vCPU/2GB).
* **Total:** **~$60/month** minimum. Costs increase if traffic spikes and scales up to `max_instance_count = 20`.



#### **4. Module: `database**` (Significant Cost)

* **What is deployed:**
* **Cloud SQL (PostgreSQL):**
* Tier: `db-g1-small` (Shared core).
* Edition: Enterprise.
* Disk: SSD (Autoscaling).
* Backups: Enabled (7 days retention).


* **Firestore:** Native mode database.


* **Cost:** **~$40 - $50 / month**.
* The SQL instance charges an hourly rate 24/7 (~$0.041/hour) plus storage costs (~$0.17/GB/month).
* Firestore is pay-as-you-go (reads/writes) and has a generous free tier.



#### **5. Module: `function**`

* **What is deployed:**
* **Cloud Function:** `pdf-ingest-function` (Python 3.11).
* **Trigger:** Eventarc trigger watching a Storage Bucket for new files.


* **Cost:** **Pay-as-you-go (Low)**.
* You only pay when a file is uploaded and the function runs. The first 2 million invocations per month are usually free.



#### **6. Module: `ingress**` (Moderate Cost)

* **What is deployed:**
* **Load Balancer:** Global External Application Load Balancer.
* **SSL:** Managed Google Certificate for `app.yourdomain.com`.
* **Cloud Armor:** Security Policy with WAF rules (SQLi, XSS, etc.) and Rate Limiting.


* **Cost:** **~$25 - $30 / month**.
* **Forwarding Rule:** The Load Balancer charges ~$0.025/hour (~$18/month).
* **Cloud Armor:** ~$5/month per policy + $1/month per rule.
* **Warning:** The plan enables `layer_7_ddos_defense_config`. Ensure you do **not** inadvertently activate "Cloud Armor Enterprise" (formerly Managed Protection Plus), which is a $3,000/month subscription. The standard pay-as-you-go version is fine, but double-check your billing console after deployment. Requires `google_compute_project_cloud_armor_tier` what we will not use here, due to costs.



#### **7. Module: `network**` (Moderate Cost)

* **What is deployed:**
* **VPC Network:** Custom subnets.
* **Cloud NAT:** A NAT Gateway (`your-actual-project-id-12345-nat`).


* **Cost:** **~$32 / month** + Data Fees.
* The NAT Gateway charges ~$0.045/hour (~$32/month) just to exist, regardless of traffic.
* You also pay $0.045 per GB for data processing through the NAT.



#### **8. Module: `redis**` (Significant Cost)

* **What is deployed:**
* **Memorystore for Redis:** Basic Tier, 1 GB capacity.


* **Cost:** **~$35 / month**.
* This is a fixed instance charged hourly (~$0.049/hour).



#### **9. Module: `storage**`

* **What is deployed:**
* **Buckets:** `data_bucket` (with lifecycle rules) and `source_bucket`.


* **Cost:** **Pay-as-you-go (Low)**.
* Standard storage is ~$0.02 per GB. Unless you store Terabytes, this is negligible.



---

### **Summary Table of Estimated Monthly "Fixed" Costs**

| Module | Resource | Est. Monthly Cost (Idle) |
| --- | --- | --- |
| **Compute** | Cloud Run (Min 1 Instance x 2 services) | ~$60.00 |
| **Database** | Cloud SQL (db-g1-small) | ~$45.00 |
| **Redis** | Memorystore (1GB Basic) | ~$35.00 |
| **Network** | Cloud NAT Gateway | ~$32.00 |
| **Ingress** | Load Balancer Rule | ~$18.00 |
| **Ingress** | Cloud Armor Policy | ~$5.00 |
| **TOTAL** | **Baseline "Rent"** | **~$195.00 / month** |

**Recommendation:**
If this is for a **development or hobby project**, this is expensive ($200/mo). To reduce costs to <$50/mo:

1. **Remove `min_instance_count = 1**` in Cloud Run (Scale to zero).
2. **Delete the Redis module** and use a local container or smaller service if possible.
3. **Delete the NAT Gateway** if your Cloud Run services don't strictly *need* a static outgoing IP (Cloud Run has a public IP by default).
4. **Downgrade Cloud SQL** to the `db-f1-micro` instance type (if available) or switch to **Cloud SQL Enterprise Plus** usually has higher minimums, sticking to standard `db-g1-small` is the cheapest managed option, or use **Firestore** only.

