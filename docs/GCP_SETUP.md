# Google Cloud Platform Setup Guide — Medrix

This guide walks through setting up a brand-new GCP account / project for Medrix from scratch.

---

## What you are setting up

| Service | Purpose |
|---|---|
| **Vertex AI** | Hosts the MedGemma 27B model for document extraction |
| **text-embedding-004** (Vertex AI) | Generates vector embeddings for RAG chat search |
| **Google Cloud Storage** | Stores uploaded medical documents |
| **Service Account** | Lets the backend authenticate to all of the above |

---

## Step 1 — Create a GCP project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown at the top → **New Project**
3. Give it a name (e.g. `medrix-ai`) and note the **Project ID** that is generated (it may differ from the name)
4. Click **Create** and wait for it to finish

> Keep the **Project ID** handy — it goes into your `.env` as `GOOGLE_CLOUD_PROJECT`.

---

## Step 2 — Enable billing

Vertex AI and Cloud Storage require a billing account.

1. In the left menu go to **Billing**
2. Link a billing account to the project (create one if you don't have one)

---

## Step 3 — Enable required APIs

Run this in [Cloud Shell](https://shell.cloud.google.com) or your local terminal with `gcloud` installed:

```bash
gcloud config set project YOUR_PROJECT_ID

gcloud services enable \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com
```

Or enable them individually in the Console under **APIs & Services → Library**:
- `Vertex AI API`
- `Cloud Storage API`
- `Identity and Access Management (IAM) API`

---

## Step 4 — Create a Service Account

This is the identity the backend uses at runtime.

1. Go to **IAM & Admin → Service Accounts**
2. Click **Create Service Account**
   - Name: `medrix-backend` (or anything you like)
   - Description: `Medrix backend service account`
3. Click **Create and Continue**
4. Grant the following roles:
   | Role | Why |
   |---|---|
   | `Vertex AI User` | Call MedGemma endpoint and embeddings |
   | `Storage Object Admin` | Upload / read documents in GCS |
5. Click **Done**

### Download the key file

1. Click on the service account you just created
2. Go to the **Keys** tab → **Add Key → Create new key**
3. Choose **JSON** → **Create**
4. A `.json` file downloads to your computer — save it somewhere safe (e.g. `~/medrix-sa-key.json`)

> **Never commit this file to git.** The backend `.gitignore` already excludes `*.json` in the backend folder.

---

## Step 5 — Create a Cloud Storage bucket

1. Go to **Cloud Storage → Buckets → Create**
2. Choose a globally unique name (e.g. `medrix-documents-yourname`)
3. **Region**: pick the same region you will deploy Vertex AI in (e.g. `europe-west4`)
4. Leave all other settings at defaults → **Create**

> Note the bucket name — it goes into your `.env` as `GCS_BUCKET_NAME`.

---

## Step 6 — Deploy MedGemma 27B on Vertex AI

MedGemma is available in **Vertex AI Model Garden**.

1. Go to **Vertex AI → Model Garden**
2. Search for **MedGemma** and select **MedGemma 27B** (multimodal)
3. Click **Deploy**
4. Configure deployment:
   - **Endpoint name**: e.g. `medrix-medgemma-endpoint`
   - **Region**: `europe-west4` (or your preferred region)
   - **Machine type**: `a2-highgpu-1g` (1× A100 40 GB) — minimum recommended
   - **Accelerator**: NVIDIA A100 40GB
5. Click **Deploy** and wait ~10–15 minutes for the endpoint to become active
6. Once active, open the endpoint and copy the **Endpoint ID** (the long numeric or slug ID in the URL / details panel)

> The Endpoint ID goes into your `.env` as `MEDGEMMA_ENDPOINT_ID`.

---

## Step 7 — Update `backend/.env`

Open `backend/.env` and fill in all the values from the steps above:

```dotenv
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id          # from Step 1
VERTEX_AI_LOCATION=europe-west4               # must match where you deployed MedGemma

# MedGemma endpoint — copy the Endpoint ID from Vertex AI → Endpoints
MEDGEMMA_ENDPOINT_ID=your-endpoint-id         # from Step 6

# Absolute path to the service account key file you downloaded
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/your-sa-key.json   # from Step 4

# Cloud Storage bucket name
GCS_BUCKET_NAME=your-bucket-name              # from Step 5

# Database (Railway PostgreSQL — no change needed if already working)
DATABASE_URL=postgresql://user:password@host:port/dbname

# Server
HOST=0.0.0.0
PORT=8000
MAX_FILE_SIZE_MB=10
```

> This is the **single source of truth** for all credentials. Every service in the backend reads from this file automatically at startup.

---

## Step 8 — Verify the setup

Start the backend and watch the startup logs:

```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload
```

You should see:
```
[GCP] Vertex AI initialized — project=your-project-id location=europe-west4
```

Then test a document upload via the frontend or directly:

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/path/to/test.pdf" \
  -F "patient_name=Test Patient"
```

---

## Troubleshooting

| Error | Likely cause | Fix |
|---|---|---|
| `google.api_core.exceptions.PermissionDenied` | Service account missing a role | Re-check Step 4 roles |
| `google.api_core.exceptions.NotFound: Endpoint not found` | Wrong endpoint ID or region | Check `MEDGEMMA_ENDPOINT_ID` and `VERTEX_AI_LOCATION` match |
| `google.cloud.exceptions.NotFound: Bucket not found` | Wrong bucket name | Check `GCS_BUCKET_NAME` in `.env` |
| `FileNotFoundError: [Errno 2] No such file or directory: '/path/to/key.json'` | Wrong credentials path | Set `GOOGLE_APPLICATION_CREDENTIALS` to the absolute path of the JSON key |
| `google.auth.exceptions.DefaultCredentialsError` | `GOOGLE_APPLICATION_CREDENTIALS` is empty | Make sure the path is set in `.env` |

---

## Cost estimate (rough)

| Resource | Approximate cost |
|---|---|
| MedGemma 27B on A100 (1 GPU) | ~$2.90/hr while running — **shut it down when not in use** |
| Cloud Storage | ~$0.02/GB/month |
| text-embedding-004 | ~$0.0001 per 1K characters |

To avoid unexpected charges, **stop or delete the Vertex AI endpoint** when you are not actively developing.

```bash
# Stop the endpoint via gcloud
gcloud ai endpoints undeploy-model ENDPOINT_ID \
  --region=europe-west4 \
  --deployed-model-id=DEPLOYED_MODEL_ID \
  --project=YOUR_PROJECT_ID
```
