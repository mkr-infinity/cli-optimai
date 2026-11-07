# Deploying OptimAI Telegram Node on Google Cloud (GCP)

This guide walks you through deploying your 24/7 OptimAI mining node on **Google Cloud Platform (GCP)** using Compute Engine.

---

## 🌟 Why Google Cloud for OptimAI Mining?

| Platform | Mining Node Capable? | Docker Engine Access | 24/7 Background | Cost |
|---|---|---|---|---|
| **Google Cloud (Compute Engine)** | ✅ **YES (100%)** | Full `/var/run/docker.sock` | Dedicated VM, never idles | Free Tier / $300 Trial Credits |
| **Railway / Render** | ❌ **NO (Control-Plane Only)** | ❌ No host Docker daemon | Sleeps on timeout | Paid monthly / container limits |
| **Local PC** | ✅ **YES** | Local Docker Desktop | Must keep PC powered on | Free (uses your electricity) |

---

## 🚀 Deployment Walkthrough (Google Cloud Console)

### Step 1: Create a Google Cloud Project & Enable Compute Engine
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Select or create a new project (e.g. `optimai-mining`).
3. Make sure billing is enabled (new accounts receive **$300 in free trial credits**).
4. Navigate to **Compute Engine** > **VM instances**.

---

### Step 2: Create a VM Instance
Click **Create Instance** and configure:
* **Name**: `optimai-node`
* **Region**: Choose a region close to you (e.g., `us-central1`, `europe-west1`, `asia-south1`).
* **Machine Configuration**:
  * **Series**: `E2`
  * **Machine Type**: `e2-micro` (2 vCPU, 1 GB memory — eligible for Free Tier) or `e2-medium` (2 vCPU, 4 GB memory for optimal performance).
* **Boot Disk**:
  * Click **Change**
  * **Operating System**: `Ubuntu`
  * **Version**: `Ubuntu 24.04 LTS` (or `Ubuntu 22.04 LTS`)
  * **Boot disk type**: `Balanced persistent disk`
  * **Size**: `20 GB` (or more)
* Click **Create**.

---

### Step 3: Connect via Web SSH
1. In the VM instances list, find `optimai-node`.
2. Click the **SSH** button next to it.
3. A terminal window will open directly in your web browser!

---

### Step 4: Clone & Run the One-Shot Setup
In the Google Cloud SSH terminal, run:

```bash
# 1. Clone the repository
git clone https://github.com/mkr-infinity/optimai-cli.git && cd optimai-cli

# 2. Run the multi-distro machine setup (installs Docker Engine & dependencies)
sudo bash setup-vps.sh

# 3. Create your configuration
cp .env.example .env
nano .env
```

Set your values in `.env`:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhI...
TELEGRAM_ALLOWED_IDS=123456789
```
Save with `Ctrl + O`, `Enter`, and exit with `Ctrl + X`.

---

### Step 5: Start the Container & Authenticate
```bash
docker compose up -d --build
docker compose logs -f
```

Open Telegram:
1. Message your bot with `/login`.
2. Authenticate with your OptimAI account.
3. Send `/start_node` to begin mining! ⛏️

---

## ⚡ Instant Deploy via `gcloud` CLI

If you have `gcloud` installed locally or use Google Cloud Shell:

```bash
# Create the Google Cloud VM instance
gcloud compute instances create optimai-node \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2404-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=25GB

# Connect to the instance
gcloud compute ssh optimai-node --zone=us-central1-a
```

---

## 🛡️ Firewall & Networking on Google Cloud

* The bot uses **Telegram long-polling (outbound HTTPS)**.
* **No inbound ports need to be opened** in your Google Cloud VPC firewall!
* All mining data and bot communications travel securely over encrypted outbound TLS.
