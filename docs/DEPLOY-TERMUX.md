# 📱 Android Termux Deployment & Mining Guide

Run your **OptimAI Telegram Bot 24/7 directly on your Android phone or tablet** using Termux! Control your node, monitor mining rewards, and manage everything from Telegram without needing an expensive cloud VPS.

---

## ⚡ Quickstart (One-Command Setup)

Open Termux on your Android device and paste:

```bash
pkg update -y && pkg install -y git curl
git clone https://github.com/mkr-infinity/cli-optimai.git
cd optimai-cli
bash setup-termux.sh
```

---

## 📋 Requirements

* **Android Phone or Tablet** (Android 7.0 or higher).
* **Termux from F-Droid** (👉 [Download Termux on F-Droid](https://f-droid.org/en/packages/com.termux/)).
  > [!WARNING]
  > **DO NOT** download Termux from the Google Play Store. The Play Store build is obsolete and fails with package repository errors. Always install the official build from F-Droid.
* **Telegram Account** and a bot token from [@BotFather](https://t.me/BotFather).
* **OptimAI Account**: [Register here with Referral Code 646D12E7](https://node.optimai.network/register?ref=646D12E7).

---

## 🛠️ Step-by-Step Installation

### Step 1: Install Termux & Configure Android Permissions

1. Open Termux on your phone.
2. Grant storage permissions so Termux can access files if needed:
   ```bash
   termux-setup-storage
   ```
3. Acquire wake lock to prevent Android battery saver from killing your node when the screen turns off:
   ```bash
   termux-wake-lock
   ```
4. **Disable Android Battery Optimization**:
   * Open Android **Settings** → **Apps** → **Termux**.
   * Go to **Battery** → Select **Unrestricted** (or "Don't optimize").

---

### Step 2: Clone & Run Automated Setup

Clone the repository and run the setup script:

```bash
git clone https://github.com/mkr-infinity/cli-optimai.git
cd optimai-cli
bash setup-termux.sh
```

The script automatically:
* Installs `python`, `git`, `screen`, `curl`, and `termux-tools`.
* Creates an isolated Python virtual environment (`.venv`).
* Installs required packages (`python-telegram-bot`, `pexpect`).
* Creates your `.env` configuration file.
* Generates a 1-tap runner script `run-termux.sh`.

---

### Step 3: Configure Your Credentials (`.env`)

Edit your `.env` file inside Termux:

```bash
nano .env
```

Enter your bot token and numeric Telegram ID:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz
TELEGRAM_ALLOWED_IDS=123456789
NODE_AUTO_START=true
CONTACT_HANDLE=@mkr_infinity
```

*Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit `nano`.*

---

### Step 4: Launch Your 24/7 Mining Bot

Start the node in the background:

```bash
bash run-termux.sh
```

This starts the bot inside a detached `screen` session. It continues running even when you close the Termux app or lock your phone.

---

## 🖥️ Screen Session Management

| Action | Command |
|---|---|
| **View live terminal session** | `screen -r optimai` |
| **Detach from session** | Press `Ctrl + A` then `D` |
| **Check running screens** | `screen -ls` |
| **View live logs** | `make logs` (or `python -m bot.main logs`) |
| **Stop background session** | Send `/stop_node` in Telegram (or `killall python`) |

---

## ⛏️ Architecture & Mining Modes on Android

### Mode 1: Termux 24/7 Remote Supervisor & Controller (Standard)
The bot runs natively in Termux, supervising your OptimAI account, syncing database credentials, monitoring rewards balance, streaming logs, and handling remote control from your phone.

### Mode 2: Full On-Device AI Mining via PRoot Ubuntu (x86_64 Emulation)
The official `optimai-cli` binary is compiled for 64-bit Linux (`x86_64`). Because Android phones use ARM64 (`aarch64`), you can run the x86_64 binary using PRoot Ubuntu and Box64:

```bash
# 1. Install Ubuntu inside Termux
pkg install -y proot-distro
proot-distro install ubuntu

# 2. Login to Ubuntu environment
proot-distro login ubuntu

# 3. Inside Ubuntu, install box64 / qemu-user-x86_64 to run the official binary:
apt update && apt install -y curl ca-certificates qemu-user-static
curl -fsSL "https://cli-node.optimai.network/optimai_cli_ubuntu" -o /usr/local/bin/optimai-cli
chmod +x /usr/local/bin/optimai-cli
```

---

## 🔋 Battery & Thermal Best Practices

1. **Keep Connected to Charger**: Continuous AI computation and background network connections consume battery. Keep your device plugged in when hosting 24/7.
2. **Wi-Fi Connection**: Use an unmetered Wi-Fi network with stable latency for optimal points generation.
3. **Cooling**: Keep your phone in a well-ventilated area (avoid placing under pillows or enclosed spaces).
4. **Wake Lock Active**: Always verify `termux-wake-lock` is enabled so Android's Doze mode does not sleep the network thread.

---

## 📱 Telegram Remote Commands

Once running in Termux, open your bot in Telegram and use:

* `/start` — Welcome overview, battery/device diagnostics, and quick buttons
* `/status` — Real-time node uptime and health report
* `/screen` — View background worker status and latest output snapshot
* `/rewards` — Check current OptimAI rewards and points
* `/logs` — View recent terminal output
* `/watch` — Live streaming log viewer in chat
* `/stop_node` — Stop background mining workloads
* `/restart_node` — Restart node & reset crash breaker

---

## 🚨 Troubleshooting & Common Error Fallbacks

### 1. `E: Repository '...' does not have a Release file` (404 Error)
* **Cause**: You installed Termux from the Google Play Store (which was deprecated in 2020).
* **Fix**:
  1. Uninstall the Google Play version of Termux.
  2. Download and install the official build from [F-Droid Termux](https://f-droid.org/en/packages/com.termux/).

---

### 2. `Unable to connect to mirror` or Package Download Timeouts
* **Cause**: The default Termux package mirror is experiencing high traffic or regional ISP blocks.
* **Fix**:
  Run the mirror selector inside Termux:
  ```bash
  termux-change-repo
  ```
  1. Select **Main repository** → Press Enter.
  2. Choose **Mirrors by Grimler** or **Mirrors by BFSU** → Press Enter.
  3. Re-run `pkg update -y`.

---

### 3. Process Killed When Phone Screen Turns Off
* **Cause**: Android OS Battery Optimization or Android 12+ "Phantom Process Killer".
* **Fix**:
  1. Run the wake lock command:
     ```bash
     termux-wake-lock
     ```
     *(A persistent notification will appear in your status bar confirming CPU stays active)*.
  2. Go to **Android Settings** → **Apps** → **Termux** → **Battery** → Select **Unrestricted**.
  3. On Samsung/Xiaomi/OnePlus: Add Termux to "Never sleeping apps" / disable "MIUI battery saver".

---

### 4. Python Build Errors (`clang: error`, `libffi`)
* **Cause**: Missing compilation tools for Python wheels on Android.
* **Fix**:
  Install build essentials in Termux:
  ```bash
  pkg install -y clang libffi openssl make python-pip
  pip install --upgrade wheel setuptools
  pip install -r requirements.txt
  ```

---

### 5. `optimai-cli: command not found` on ARM64 Phone
* **Cause**: The official OptimAI CLI binary is compiled for x86_64, but your phone is ARM64.
* **Fix**:
  Run our automated PRoot x86_64 bridge installer:
  ```bash
  bash setup-termux-proot.sh
  ```
  This automatically provisions Ubuntu rootfs with QEMU x86_64 emulation and creates a transparent `$PREFIX/bin/optimai-cli` bridge in Termux.

---

### 6. `Cannot start node: no Docker daemon here`
* **Explanation**: On non-rooted Android, the native Docker daemon cannot start because the Android kernel restricts container namespaces.
* **How it works**:
  * **Option A (Phone Supervisor)**: The bot runs 24/7 on your phone, syncing credentials, monitoring rewards, and giving you complete remote control.
  * **Option B (Full Mining)**: Run `bash setup-termux-proot.sh` to run the official CLI worker inside PRoot.
