# GCP Infrastructure Management Guide for AI Copilots

This document details the configuration, deployment, and management workflows for the **HIT DAW** project backend on Google Cloud Platform (GCP). It is designed to be read and executed by AI agents/copilots.

---

## ⚠️ Critical Environment Requirements

Before running any `gcloud` command, you **MUST** prefix it with the following Python environment variable. If omitted, the gcloud CLI will fail with a Python version incompatibility error.

```bash
export CLOUDSDK_PYTHON="/opt/homebrew/bin/python3"
```

Alternatively, prefix every command:
```bash
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3 /Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud <command>
```

Always append `2>&1` to capture both stdout and stderr for analysis.

---

## 1. Project Reference

- **GCP Project ID:** `sage-tribute-381522`
- **Active GCP Account:** `claytonbwashington@gmail.com`
- **gcloud CLI Location:** `/Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud`

### Verify Configuration
```bash
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3 /Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud config list 2>&1
```

### Set Project
```bash
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3 /Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud config set project sage-tribute-381522 2>&1
```

---

## 2. Pre-requisite: Billing Account Setup

> [!IMPORTANT]
> The current billing account `My Billing Account (019F2C-9AF10E-204DCC)` is closed/inactive.
> The Compute Engine API cannot be enabled, and instances cannot be created until this is resolved.

### Reopen Billing Account (Must be done via Google Cloud Console):
1. Go to the [Google Cloud Console Billing Page](https://console.cloud.google.com/billing).
2. Clear the filter **Status: Active** to display closed billing accounts.
3. Click on **My Billing Account (019F2C-9AF10E-204DCC)**.
4. Click **Reopen billing account** at the top of the page.
5. Ensure a valid credit card or payment method is attached.

---

## 3. Compute Engine API Enablement

Once billing is open, run the following command to enable the Compute Engine API:

```bash
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3 /Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud services enable compute.googleapis.com 2>&1
```

---

## 4. Compute Instance Details

- **Target Instance Name:** `hit-daw-server`
- **Region/Zone:** `us-central1-a` (selected for low cost)
- **Machine Type:** `e2-micro` (cheapest tier, suitable for lightweight git server/FastAPI)
- **OS Image:** Ubuntu 22.04 LTS (`ubuntu-2204-lts` from `ubuntu-os-cloud` project)
- **Boot Disk:** `20GB` Standard Persistent Disk (`pd-standard`) for LFS audio storage.
- **Firewall Tags:** `http-server`, `https-server`, `http-8000`

### Provision Instance
```bash
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3 /Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud compute instances create hit-daw-server \
    --project=sage-tribute-381522 \
    --zone=us-central1-a \
    --machine-type=e2-micro \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --boot-disk-type=pd-standard \
    --tags=http-server,https-server,http-8000 \
    --metadata=enable-oslogin=TRUE \
    --quiet 2>&1
```

---

## 5. Networking & Firewall Configuration

To serve the FastAPI application, port `8000` must be accessible.

### Allow Traffic on Port 8000
```bash
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3 /Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud compute firewall-rules create allow-http-8000 \
    --project=sage-tribute-381522 \
    --allow=tcp:8000 \
    --target-tags=http-8000 \
    --description="Allow incoming traffic on port 8000 for FastAPI" \
    --direction=INGRESS \
    --quiet 2>&1
```

---

## 6. Post-Deployment Commands

### Fetch External IP
Run this command to retrieve the newly assigned public IP:
```bash
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3 /Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud compute instances describe hit-daw-server \
    --project=sage-tribute-381522 \
    --zone=us-central1-a \
    --format="get(networkInterfaces[0].accessConfigs[0].natIP)" 2>&1
```

### SSH into Instance
```bash
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3 /Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud compute ssh hit-daw-server \
    --project=sage-tribute-381522 \
    --zone=us-central1-a 2>&1
```

### Instance Control (Power Operations)
```bash
# Start Instance
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3 /Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud compute instances start hit-daw-server --project=sage-tribute-381522 --zone=us-central1-a --quiet 2>&1

# Stop Instance
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3 /Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud compute instances stop hit-daw-server --project=sage-tribute-381522 --zone=us-central1-a --quiet 2>&1

# Status check
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3 /Users/claywashington/Downloads/google-cloud-sdk/bin/gcloud compute instances list --project=sage-tribute-381522 2>&1
```
