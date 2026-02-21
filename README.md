# School Voting System — Complete Setup Guide

This guide walks you through every step to set up the school voting kiosk, from unboxing the hardware to students tapping cards on voting day. It assumes you have never used a Raspberry Pi or typed commands into a computer before. Every step is explained.

**Estimated total setup time:** 2–3 hours the first time.

---

## Table of Contents

1. [What This System Does](#1-what-this-system-does)
2. [Shopping List](#2-shopping-list)
3. [Physical Assembly](#3-physical-assembly)
4. [Install Raspberry Pi OS](#4-install-raspberry-pi-os)
5. [First Boot and Basic Configuration](#5-first-boot-and-basic-configuration)
6. [Enable the I2C Interface](#6-enable-the-i2c-interface)
7. [Confirm the NFC Reader is Detected](#7-confirm-the-nfc-reader-is-detected)
8. [Copy the Voting System Files to the Pi](#8-copy-the-voting-system-files-to-the-pi)
9. [Install the Software](#9-install-the-software)
10. [Run First-Time Setup](#10-run-first-time-setup)
11. [Test the System Manually](#11-test-the-system-manually)
12. [Set Up Google Sheets (Optional but Recommended)](#12-set-up-google-sheets-optional-but-recommended)
13. [Make the System Start Automatically on Boot](#13-make-the-system-start-automatically-on-boot)
14. [Prevent the Screen from Going to Sleep](#14-prevent-the-screen-from-going-to-sleep)
15. [Final Verification Checklist](#15-final-verification-checklist)
16. [Weekly Admin Workflow](#16-weekly-admin-workflow)
17. [Managing Student Cards](#17-managing-student-cards)
18. [Troubleshooting](#18-troubleshooting)
19. [Reference: What Each File Does](#19-reference-what-each-file-does)

---

## 1. What This System Does

Students are each given an RFID card (a small plastic card with a chip inside, similar to a hotel key card). When they tap their card on the reader, a question appears on the screen with 2 to 4 answer buttons. They touch their answer, see the current results as a bar chart for 15 seconds, and the screen returns to the welcome screen for the next student.

The admin (that's you) sets the weekly question using a password-protected web page on the same computer. Results can be downloaded as a spreadsheet file or synced directly to Google Sheets.

---

## 2. Shopping List

Purchase all of the following items before starting. Links are provided as examples — any equivalent product will work.

> **This guide supports both Raspberry Pi 3 and Raspberry Pi 4.** The Pi 3 works perfectly well for this system. There are two hardware differences between the models — they are highlighted in the table below. Everything else (software, NFC HAT, setup steps) is identical.

| # | Item | What it is | Pi 3 note | Where to find it |
|---|------|-----------|-----------|-----------------|
| 1 | **Raspberry Pi 3 Model B or B+** (or Pi 4 Model B) | The small computer that runs everything. Either model works fine for this project. | — | raspberrypi.com, Amazon, Adafruit |
| 2 | **Power Supply** | A power adapter made specifically for the Pi. Do not use a random phone charger — it may not supply enough power and can cause random crashes. | **Pi 3 uses Micro-USB** (same connector as older Android phones). Pi 4 uses USB-C. Make sure you buy the right one for your model. | Same stores as above |
| 3 | **MicroSD Card, 32GB or larger, Class 10 or faster** | The Pi's "hard drive." A SanDisk Endurance or Samsung Endurance card is a good choice — they are designed for continuous use. | — | Amazon, Best Buy |
| 4 | **MicroSD card reader** | A small USB adapter to plug the MicroSD card into your Windows computer. Many laptops have one built in. | — | Amazon (~$8) |
| 5 | **Coolwell PN532 NFC HAT** | The card reader. It attaches directly to the top of the Raspberry Pi. Search "PN532 NFC HAT Raspberry Pi I2C" on Amazon. | Works on both Pi 3 and Pi 4 — same connection, same setup. | Amazon (~$15–$25) |
| 6 | **HDMI Monitor** | Any standard computer monitor with an HDMI input. | — | Any electronics store |
| 7 | **HDMI Cable** | Connects the Pi to your monitor. | **Pi 3 has a standard full-size HDMI port** — use a regular HDMI cable (same type you would use for a TV). Pi 4 has a Micro-HDMI port and needs a Micro-HDMI to HDMI cable instead. | Amazon (~$8) |
| 8 | **USB Touchscreen Overlay** | A frame that clips over your monitor and adds touch input. Search "USB touchscreen overlay 21 inch" (or whatever size your monitor is). | — | Amazon (~$40–$80) |
| 9 | **USB Mouse and Keyboard** | Only needed during setup. Any cheap USB mouse and keyboard work. | — | Any electronics store |
| 10 | **200+ RFID Cards (MIFARE Classic 1K, 13.56 MHz)** | The student cards. Must say "MIFARE Classic" or "NFC 13.56MHz." Do not buy 125kHz cards — they will not work. | — | Amazon (search "MIFARE Classic RFID cards") |

**You will also need:**
- A Windows, Mac, or Linux computer to prepare the SD card (your regular computer)
- An internet connection on the Raspberry Pi (WiFi or ethernet cable)

---

## 3. Physical Assembly

### Step 3A — Attach the NFC HAT to the Raspberry Pi

The PN532 HAT has a row of holes along one edge that line up with the metal pins on top of the Raspberry Pi. This connection is called the "GPIO header."

1. Place the Raspberry Pi on a flat surface with the GPIO pins (the two rows of thin metal pins) facing up.
2. Look at the NFC HAT — find the row of square holes on the bottom edge. This is the connector.
3. Hold the HAT directly above the Pi so the holes line up with all 40 pins.
4. Press the HAT down firmly and evenly until it is fully seated. You should feel it click into place and the HAT will sit flat against the Pi. It takes more force than you expect — push firmly.
5. **Check that every pin went into a hole and none are bent sideways.** If any pin is bent, gently straighten it with a fingernail before continuing.

**Important — set the HAT's jumpers to I2C mode:**
The PN532 HAT has tiny plastic "jumpers" (small black rectangular clips) on the board. Check the label printed on the HAT near the jumpers. You need to set it to **I2C mode**. The jumper positions for I2C are typically:
- SCL jumper: short the two pins labeled **SCL**
- SDA jumper: short the two pins labeled **SDA**

Your HAT should come with a small sheet showing the jumper positions. If the HAT has a switch instead of jumpers, slide it to the position labeled **I2C**.

### Step 3B — Connect the Touchscreen

1. Follow the instructions that came with your touchscreen overlay to physically attach it to the front of your monitor.
2. Connect the touchscreen's USB cable to any USB port on the Raspberry Pi.
3. This is all that is required — no driver installation needed.

### Step 3C — Connect the Monitor

**If you have a Pi 3:**
1. Connect one end of a standard HDMI cable to the single HDMI port on the Pi 3 (it is a full-size port on the side of the board).
2. Connect the other end to your monitor's HDMI port.

**If you have a Pi 4:**
1. Connect one end of a Micro-HDMI cable to the port labeled **HDMI 0** on the Pi 4 (the one closer to the USB-C power port).
2. Connect the other end to your monitor's HDMI port.

### Step 3D — Connect the Mouse and Keyboard

Plug the USB mouse and keyboard into any of the four USB ports on the Raspberry Pi. You only need these during setup.

### Step 3E — Do NOT connect power yet

Do not plug in the power supply. You will do that in a later step, after the SD card is prepared.

---

## 4. Install Raspberry Pi OS

The Raspberry Pi needs an operating system (like Windows, but for the Pi) installed on the MicroSD card. This is done from your regular Windows computer.

### Step 4A — Download Raspberry Pi Imager

1. On your regular Windows computer, open a web browser and go to:
   **https://www.raspberrypi.com/software/**
2. Click the big button **Download for Windows**.
3. Once downloaded, open the installer file and follow the on-screen steps to install it. Click Next, accept the agreement, click Install. It takes about 30 seconds.

### Step 4B — Prepare the MicroSD Card

1. Insert the MicroSD card into your card reader, then plug the card reader into your Windows computer.
2. Open **Raspberry Pi Imager** from the Start Menu.
3. You will see three buttons. Click **CHOOSE DEVICE** and select your Pi model — **Raspberry Pi 3** or **Raspberry Pi 4** depending on what you have. (Look at the board — the model is printed on it.)
4. Click **CHOOSE OS**. Select **Raspberry Pi OS (other)**, then select **Raspberry Pi OS with desktop** (the full version, NOT the Lite version — you need the desktop).
5. Click **CHOOSE STORAGE** and select your MicroSD card from the list. **Be careful — selecting the wrong drive will erase it.** The card is usually the smallest drive in the list.
6. Click **NEXT**.
7. A dialog will ask "Would you like to apply OS customisation settings?" Click **EDIT SETTINGS**.
8. In the settings window, fill in the following:
   - **Set hostname:** `votingkiosk` (no spaces)
   - **Set username and password:** Username must be `pi`. Choose a password you will remember.
   - **Configure wireless LAN:** Enter your school's WiFi network name and password. Set **Wireless LAN country** to your country.
   - **Set locale settings:** Choose your timezone and keyboard layout.
9. Click **SAVE**, then click **YES** to apply the settings.
10. Click **YES** on the warning that says all data on the card will be erased.
11. The Imager will download and write Raspberry Pi OS. This takes 5–15 minutes depending on your internet speed. A progress bar is shown. **Do not remove the card while it is writing.**
12. When it says "Write Successful," click **CONTINUE** and remove the MicroSD card.

### Step 4C — Insert the Card and Boot the Pi

1. Insert the MicroSD card into the MicroSD card slot on the underside of the Raspberry Pi. The gold contacts face down. Push it in until it clicks.
2. Plug in the power supply.
3. The Pi will boot. The monitor will show a rainbow screen briefly, then the Raspberry Pi desktop will appear. This takes about 60–90 seconds the first time.

---

## 5. First Boot and Basic Configuration

When the desktop first appears, a setup wizard may appear. Follow it:

1. **Welcome screen** — click **Next**.
2. **Country** — confirm your country, language, and timezone are correct. Click **Next**.
3. **Create user** — if asked, confirm username `pi` and your password.
4. **Set up screen** — if the desktop doesn't fill your monitor, check the box and click **Next**.
5. **Connect to WiFi** — if not already connected from the Imager settings, select your network and enter the password. Click **Next**.
6. **Update software** — click **Next** to let the Pi download updates. This can take several minutes. **Do not skip this step.**
7. **Setup complete** — click **Restart**.

The Pi will restart and return to the desktop.

### How to Open the Terminal

You will type commands throughout this guide. The **Terminal** is a text window where you type instructions for the computer.

To open the Terminal:
- Look at the top-left of the screen for the **taskbar** with icons.
- Click the icon that looks like a black rectangle with a `>_` symbol. This is the Terminal.
- Alternatively, click the **Raspberry Pi menu** (top-left raspberry icon) → **Accessories** → **Terminal**.

A black window will appear with a line that ends in `$`. This is the command prompt — it means the Pi is ready for your next instruction.

### How to Type Commands

When this guide shows a line starting with `$`, that means you type everything AFTER the `$` sign and then press **Enter**. Do not type the `$` itself.

For example, if the guide says:
```
$ echo hello
```
You type `echo hello` and press Enter.

**Typing tips:**
- Commands are case-sensitive. `ls` and `LS` are different.
- Copy-pasting: in the Terminal, right-click → Paste (Ctrl+V does not work in most terminals).
- If you make a mistake, press Ctrl+C to cancel and start over.
- If asked for your password, type it and press Enter. The cursor will not move while typing your password — this is normal.

---

## 6. Enable the I2C Interface

The NFC HAT communicates with the Pi using a protocol called I2C. It is disabled by default and must be turned on.

1. Open the Terminal.
2. Type the following and press Enter:
   ```
   sudo raspi-config
   ```
   A blue menu will appear. Use the **arrow keys** on your keyboard to navigate, and **Enter** to select.

3. Navigate to **Interface Options** and press Enter.
4. Navigate to **I2C** and press Enter.
5. When asked "Would you like the ARM I2C interface to be enabled?" select **Yes** and press Enter.
6. Press Enter to acknowledge the confirmation message.
7. Navigate to **Finish** and press Enter.
8. If asked to reboot, select **Yes**. If not, type the following and press Enter:
   ```
   sudo reboot
   ```
9. Wait for the Pi to restart and the desktop to return.

---

## 7. Confirm the NFC Reader is Detected

This step checks that the NFC HAT is properly connected and the Pi can "see" it.

1. Open the Terminal.
2. Install the I2C detection tool by typing and pressing Enter:
   ```
   sudo apt install -y i2c-tools
   ```
   You will see lines of text as things install. Wait for the command prompt `$` to reappear.

3. Now scan for I2C devices:
   ```
   i2cdetect -y 1
   ```

4. A grid of dashes will appear. Look for a number in the grid. It should show `24` at the position for address 0x24. The output looks like this:
   ```
        0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
   00:          -- -- -- -- -- -- -- -- -- -- -- -- --
   10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
   20: -- -- -- -- 24 -- -- -- -- -- -- -- -- -- -- --
   30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
   ```
   The `24` in the row labeled `20:` means the PN532 is found at address 0x24. ✅

**If you do NOT see any number in the grid (all dashes):**
- Power off the Pi, check that the HAT is firmly seated on all 40 GPIO pins, and check that the jumpers are set to I2C mode. Then boot again and repeat this step.

**If you see a number other than `24`** (for example `48`):
- You need to tell the software about this. Follow the instructions in [Troubleshooting](#18-troubleshooting) under "Wrong I2C address."

---

## 8. Copy the Voting System Files to the Pi

The voting system files are currently on your Windows computer in the folder `C:\Users\joshv\voting-system\`. You need to copy them to the Raspberry Pi.

The easiest method is a USB drive.

### Step 8A — Copy Files to a USB Drive (on your Windows computer)

1. Plug a USB drive into your Windows computer.
2. Open **File Explorer** (the folder icon in the taskbar).
3. Navigate to `C:\Users\joshv\` — you should see the `voting-system` folder.
4. Right-click the `voting-system` folder and click **Copy**.
5. In File Explorer, click on your USB drive on the left side.
6. Right-click in the empty space on the USB drive and click **Paste**.
7. Wait for the copy to finish (the folder is small, it will take a few seconds).
8. Safely eject the USB drive: right-click the USB drive in File Explorer → **Eject**.

### Step 8B — Copy Files from USB Drive to the Pi

1. Plug the USB drive into one of the USB ports on the Raspberry Pi.
2. A file manager window may open automatically. Close it.
3. Open the Terminal on the Pi.
4. Type the following command to copy the folder. (This assumes your USB drive is named something like `USB` — check by typing `ls /media/pi/` first to see what it's called, then replace `USB` with the actual name.)
   ```
   ls /media/pi/
   ```
   This shows you the name of your USB drive. For example, it might show `USB` or `ESD-USB` or a random string of letters and numbers.

5. Copy the files using that name (replace `USB` with the actual name you saw):
   ```
   cp -r /media/pi/USB/voting-system /home/pi/voting-system
   ```
   Wait for the command prompt to return. No output means it worked.

6. Confirm the files arrived:
   ```
   ls /home/pi/voting-system
   ```
   You should see files listed including `app.py`, `config.py`, `database.py`, etc.

7. You can now unplug the USB drive.

---

## 9. Install the Software

The voting system is written in Python. Before it can run, you need to install its dependencies (other software it relies on). This requires an internet connection.

### Step 9A — Install System Packages

Open the Terminal and type the following commands one at a time. After each one, press Enter and wait for it to finish (the `$` prompt will reappear).

Install system tools:
```
sudo apt install -y unclutter chromium-browser
```
This installs the Chromium web browser (for the kiosk screen) and `unclutter` (which hides the mouse cursor). This may take a few minutes.

Install the hardware library for the NFC reader:
```
sudo pip3 install --break-system-packages adafruit-blinka
```
This installs the Adafruit CircuitPython layer that lets Python talk to the NFC HAT.

### Step 9B — Create a Python Virtual Environment

A "virtual environment" is an isolated box for the app's Python packages so they don't interfere with the rest of the Pi's software.

Navigate to the voting system folder:
```
cd /home/pi/voting-system
```

Create the virtual environment:
```
python3 -m venv venv --system-site-packages
```
The `--system-site-packages` flag means the virtual environment can see the NFC library you installed in the previous step.

Activate the virtual environment (you will need to do this any time you work in the Terminal):
```
source venv/bin/activate
```
After this, your prompt will change to show `(venv)` at the beginning — for example `(venv) pi@votingkiosk:~$`. This means the virtual environment is active.

### Step 9C — Install Python Packages

```
pip install -r requirements.txt
```
This reads the `requirements.txt` file and installs all the Python packages the voting system needs. You will see a lot of text scroll by. This takes 3–10 minutes. Wait for the `$` prompt to return.

---

## 10. Run First-Time Setup

This step creates the database, generates a secret security key, and sets your admin password.

Make sure you are in the voting system folder with the virtual environment active (you should see `(venv)` in your prompt). If not:
```
cd /home/pi/voting-system
source venv/bin/activate
```

Now run the setup wizard:
```
python app.py --setup
```

You will see:
```
=== School Voting System — First-Time Setup ===

Secret key generated.
Database initialised.

Set admin password (min 6 chars):
```

Type a password for the admin panel and press Enter. The cursor will not move — that is normal for password entry. You will be asked to type it again to confirm.

When setup completes you will see:
```
Admin password set.

Setup complete!
  Start server:  python app.py
  Admin panel:   http://127.0.0.1:5000/admin
```

---

## 11. Test the System Manually

Before setting up auto-start, confirm everything works by running the server by hand.

Make sure the virtual environment is active and you are in the right folder:
```
cd /home/pi/voting-system
source venv/bin/activate
```

Start the server:
```
python app.py
```

You will see log messages appear:
```
INFO nfc_reader: PN532 ready at I2C 0x24
INFO app: Starting server on 127.0.0.1:5000
```

Now open the **Chromium** browser on the Pi:
- Click the **Globe** icon in the taskbar, or go to the Raspberry Pi menu → Internet → Chromium Web Browser.
- In the address bar, type `http://127.0.0.1:5000` and press Enter.
- You should see a blue screen that says **"School Vote! Tap Your Card to Vote."** ✅

Open the admin panel by typing `http://127.0.0.1:5000/admin` in the address bar. Log in with the password you set during setup.

**Create a test voting session:**
1. Click **Sessions** in the top navigation bar.
2. Click **+ New Session**.
3. Fill in:
   - Question: `What is your favourite colour?`
   - Option A: `Red`
   - Option B: `Blue`
   - Option C: `Green`
   - Start Time: a time a few minutes in the past (so it is already open)
   - End Time: a time several hours from now
4. Click **Create Session**.

Go back to `http://127.0.0.1:5000` — the welcome screen should now show the question.

**Enroll a test card:**
1. In the admin panel, click **Cards**.
2. Tap one of your RFID cards on the PN532 reader.
3. The UID (a series of letters and numbers like `A3:F2:01:9C`) should automatically appear in the "Card UID" field.
4. Optionally type a label like `Test Card`.
5. Click **Enroll**.

**Test voting:**
- On the welcome screen (`http://127.0.0.1:5000`), tap the card you just enrolled.
- The screen should jump to the voting page showing your question and options.
- Tap one of the coloured buttons.
- The "Thank you" screen appears with a bar chart.
- After 15 seconds it returns to the welcome screen automatically. ✅

When you are finished testing, return to the Terminal and press **Ctrl+C** to stop the server.

---

## 12. Set Up Google Sheets (Optional but Recommended)

This section lets the voting system automatically send results to a Google Sheet. If you do not want this feature, skip to [Section 13](#13-make-the-system-start-automatically-on-boot).

This takes about 20 minutes.

### Step 12A — Create a Google Cloud Project

> A "Google Cloud Project" is a free workspace that lets you use Google's APIs (tools). You are not being charged for this.

1. On any computer (not necessarily the Pi), open a browser and go to:
   **https://console.cloud.google.com/**
2. Sign in with a Google account. A school Gmail account works.
3. At the top of the page, click the project dropdown (it may say "Select a project" or show an existing project name).
4. Click **NEW PROJECT**.
5. Name it `school-voting` and click **CREATE**.
6. Wait a few seconds, then click the notification bell (top right) to see when the project is ready. Click on the project name when it appears.

### Step 12B — Enable the Required APIs

1. In the left menu, click **APIs & Services** → **Library**.
2. In the search box, type `Google Sheets API`. Click on it in the results.
3. Click the blue **ENABLE** button. Wait a moment.
4. Click the back arrow to go back to the library.
5. Search for `Google Drive API`. Click on it, then click **ENABLE**.

### Step 12C — Create a Service Account

A "service account" is like a robot user that your Pi will log in as to access the spreadsheet.

1. In the left menu, click **IAM & Admin** → **Service Accounts**.
2. Click **+ CREATE SERVICE ACCOUNT** at the top.
3. In the "Service account name" field, type `voting-system`. The "Service account ID" field will auto-fill.
4. Click **CREATE AND CONTINUE**.
5. Skip the optional steps — click **CONTINUE**, then **DONE**.
6. You will see the service account listed. Click on it.
7. Click the **KEYS** tab.
8. Click **ADD KEY** → **Create new key**.
9. Make sure **JSON** is selected, then click **CREATE**.
10. A JSON file will download to your computer. **Keep this file safe — it gives access to your Google Sheet.**

### Step 12D — Copy the Key File to the Pi

The JSON key file needs to go on the Raspberry Pi.

**Using a USB drive:**
1. Copy the downloaded JSON file to a USB drive.
2. Plug the USB drive into the Pi.
3. In the Terminal on the Pi, copy the file (replace `USB` and the filename with your actual values):
   ```
   cp /media/pi/USB/your-file-name.json /home/pi/voting-system/credentials/google_service_account.json
   ```
4. Protect the file so only the Pi can read it:
   ```
   chmod 600 /home/pi/voting-system/credentials/google_service_account.json
   ```

### Step 12E — Create and Share the Google Sheet

1. On any computer, go to **https://sheets.google.com** and create a new blank spreadsheet.
2. Name it something like `School Voting Results`.
3. Open the JSON file you downloaded earlier in a text editor (Notepad on Windows: right-click → Open with → Notepad).
4. Find the line that says `"client_email":`. Copy the email address in quotes — it looks like: `voting-system@school-voting-XXXXXX.iam.gserviceaccount.com`
5. Go back to your Google Sheet. Click the green **Share** button (top right).
6. Paste the service account email address into the "Add people and groups" box.
7. Make sure the permission is set to **Editor** (not Viewer).
8. Click **Send** (ignore the "this is not a Google account" message — that is normal).

### Step 12F — Get the Spreadsheet ID

Look at the URL of your Google Sheet in the browser address bar. It looks like this:
```
https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit
```
The long string of letters and numbers between `/d/` and `/edit` is the **Spreadsheet ID**. Copy it.

### Step 12G — Enter the ID in the Admin Panel

1. Open the admin panel (`http://127.0.0.1:5000/admin`).
2. Click **Settings** in the top navigation.
3. Paste the Spreadsheet ID into the field.
4. Check the box **Enable Google Sheets sync**.
5. Click **Save Settings**.

From now on, after each vote the system will automatically update the Google Sheet in the background.

---

## 13. Make the System Start Automatically on Boot

Right now you have to open the Terminal and type `python app.py` every time you turn on the Pi. These steps make the system start by itself whenever the Pi is powered on, just like a real appliance.

Open the Terminal and type each command, pressing Enter after each one:

**Copy the service files to the system folder:**
```
sudo cp /home/pi/voting-system/systemd/voting-backend.service /etc/systemd/system/
sudo cp /home/pi/voting-system/systemd/voting-kiosk.service /etc/systemd/system/
```

**Tell systemd to reload its list of services:**
```
sudo systemctl daemon-reload
```

**Enable both services so they start on every boot:**
```
sudo systemctl enable voting-backend
sudo systemctl enable voting-kiosk
```

**Start the backend service right now (without waiting for a reboot):**
```
sudo systemctl start voting-backend
```

**Verify the backend is running:**
```
sudo systemctl status voting-backend
```

You should see output that includes the words **active (running)** in green. Press **Q** to exit the status view.

**Reboot to confirm everything starts automatically:**
```
sudo reboot
```

After the Pi restarts (about 60 seconds), the Chromium browser should open automatically and show the voting welcome screen full-screen. If it does not appear immediately, wait an extra 30 seconds — the browser waits for the backend to start first.

---

## 14. Prevent the Screen from Going to Sleep

By default, the Pi's screen will go dark after a few minutes of inactivity. On a kiosk, you want the screen on all the time.

### Step 14A — Edit the autostart file

Open the Terminal and type:
```
nano /home/pi/.config/lxsession/LXDE-pi/autostart
```
This opens a text editor called `nano`. You will see a few lines of text already in the file.

Use the **arrow keys** to move to the very end of the file, then add these four lines (press Enter after each):
```
@xset s off
@xset -dpms
@xset s noblank
@unclutter -idle 0.5 -root
```

When done, press **Ctrl+X** to exit, then press **Y** to confirm saving, then press **Enter**.

### Step 14B — Disable screen blanking in system settings

1. Click the **Raspberry Pi menu** (raspberry icon, top left).
2. Go to **Preferences** → **Raspberry Pi Configuration**.
3. Click the **Display** tab.
4. Set **Screen Blanking** to **Disabled**.
5. Click **OK**.

### Step 14C — Reboot to apply

```
sudo reboot
```

The screen should now stay on indefinitely.

---

## 15. Final Verification Checklist

Before putting the kiosk in front of students, work through this checklist. Each item should be ticked off before moving to the next.

- [ ] **Pi boots to the kiosk welcome screen automatically** — after a full power cycle (unplug and replug the power), the blue "Tap Your Card to Vote" screen appears without you doing anything.
- [ ] **NFC reader detected** — open Terminal, type `i2cdetect -y 1`, confirm a number appears in the grid.
- [ ] **Card enrollment works** — Admin → Cards, tap a card, UID fills in, click Enroll, card appears in the list.
- [ ] **Voting works** — tap an enrolled card on the welcome screen, choose an answer, see the results bar chart, watch it return to the welcome screen after 15 seconds.
- [ ] **Duplicate vote is blocked** — tap the same card again immediately after voting, see the "Already voted" error message for 5 seconds.
- [ ] **Unregistered card is blocked** — tap a card that has NOT been enrolled, see the "Card not registered" message.
- [ ] **Session time works** — create a session with an end time in the past, confirm the welcome screen shows the "Voting Closed" screen instead of the question.
- [ ] **CSV export works** — Admin → Export, click Download CSV, open the file, confirm it shows the correct votes.
- [ ] **Screen does not go to sleep** — leave the Pi on and untouched for 15 minutes, confirm the screen stays on.
- [ ] **Auto-start works** — unplug the power, wait 10 seconds, plug it back in, confirm the kiosk screen comes back on its own.

---

## 16. Weekly Admin Workflow

### Every Monday Morning — Set Up This Week's Vote

The admin panel is accessed from any browser (on the Pi itself or on another computer on the same network).

From the Pi: open Chromium and go to `http://127.0.0.1:5000/admin`
From another computer on the same network: go to `http://votingkiosk.local:5000/admin`

> **Note:** To access the admin panel from another computer, you may first need to find the Pi's IP address by opening Terminal on the Pi and typing `hostname -I`.

1. Log in with your admin password.
2. Click **Sessions** in the top navigation bar.
3. Click **+ New Session**.
4. Fill in:
   - **Question** — the week's voting question, e.g. `What should we have for the class party?`
   - **Option A** — first answer, e.g. `Pizza`
   - **Option B** — second answer, e.g. `Hot Dogs`
   - **Option C** — third answer (optional), e.g. `Sandwiches`
   - **Option D** — fourth answer (optional, leave blank if not needed)
   - **Start Time** — when voting should open, e.g. Monday 8:00 AM
   - **End Time** — when voting should close, e.g. Friday 3:00 PM
5. Click **Create Session**.

The kiosk welcome screen will automatically show the new question once the start time is reached.

### During the Week — Check Results

1. Admin panel → **Results**.
2. A bar chart updates automatically every 10 seconds.

### Every Friday — Export Results

**Download as CSV (spreadsheet file):**
1. Admin panel → **Export**.
2. Make sure the current session is selected in the dropdown.
3. Click **Download CSV**.
4. Open the file in Excel or Google Sheets.

**Sync to Google Sheets:**
1. Admin panel → **Export**.
2. Click **Sync to Google Sheets**.
3. Wait a few seconds. A green success message will appear confirming the sync.
4. Open your Google Sheet to see the Summary and Detail tabs updated.

---

## 17. Managing Student Cards

### Enrolling Cards (Adding New Students)

Do this before the first week of voting, then again any time a new student joins.

1. Open the admin panel → click **Cards**.
2. Tap a card on the NFC reader.
3. The UID (e.g. `A3:F2:01:9C`) will appear in the Card UID field automatically.
4. Type an optional label in the Label field — this helps you identify whose card it is, e.g. `Room 4 — Card 17`.
5. Click **Enroll**.
6. Repeat for each card.

**Tip:** You can do a batch enrollment session before school starts — just keep tapping cards one by one. Each tap auto-fills the UID, you add a label, click Enroll, and move to the next card.

Newly enrolled cards can vote immediately, even during an active session.

### Deactivating a Card (Lost or Broken Card)

1. Admin panel → **Cards**.
2. Find the card in the list (by UID or label).
3. Click **Deactivate**.
4. The card is blocked immediately — if that student taps it, they will see "Card not registered."
5. The card remains in the list as Inactive (for your records). It is not deleted.

When the student gets a replacement card, enroll the new card and give it the same label.

### The Same Voter List Each Week

The card list stays the same from week to week — you only need to enroll cards once. Only the voting question changes. The system automatically resets who has voted when you create a new session.

---

## 18. Troubleshooting

### "The screen is black / nothing happens after booting"
- Wait up to 90 seconds — the first boot is slow.
- **Pi 3:** Confirm the HDMI cable is firmly in the full-size HDMI port on the side of the board.
- **Pi 4:** Confirm the Micro-HDMI cable is in the port labeled **HDMI 0** (closest to the USB-C power port).
- Try a different HDMI cable.

### "i2cdetect shows no numbers / all dashes"
The Pi cannot see the NFC HAT.
1. Power off the Pi (unplug the power).
2. Firmly re-seat the HAT on the GPIO header — press harder than you think necessary.
3. Check that the HAT jumpers are set to I2C mode (see Step 3A).
4. Make sure I2C is enabled (repeat Step 6).
5. Power on and try again.

### "The NFC reader shows a different address (not 24)"
You need to tell the software about the correct address.
1. Open the Terminal.
2. Type: `nano /home/pi/voting-system/config.py`
3. Find the line: `NFC_I2C_ADDRESS = 0x24`
4. Change `0x24` to match the address shown by `i2cdetect -y 1`. For example, if it showed `48`, change it to `0x48`.
5. Press **Ctrl+X**, then **Y**, then **Enter** to save.
6. Restart the voting service: `sudo systemctl restart voting-backend`

### "Card taps twice / counts two votes for one tap"
The scanner is too sensitive. Increase the cooldown time.
1. Type: `nano /home/pi/voting-system/config.py`
2. Find the line: `SCAN_COOLDOWN = 2.0`
3. Change `2.0` to `3.0` or higher.
4. Save and restart: `sudo systemctl restart voting-backend`

### "The kiosk screen shows the admin page / wrong page"
The browser may have saved a session from previous testing. Open Chromium manually and navigate to `http://127.0.0.1:5000` to reset.

### "Chromium shows a 'restore session' dialog on startup"
This is already suppressed in the service file configuration. If it appears, click **Don't restore** and it should not appear again after the next reboot.

### "Touch input is rotated / upside down"
The touchscreen coordinates don't match the display.
1. Open Terminal and type:
   ```
   ls /dev/input/
   ```
2. Note the device listed (e.g. `event0`).
3. Type: `sudo nano /usr/share/X11/xorg.conf.d/40-touch.conf`
4. Add this (adjusting `Identifier` to match your device):
   ```
   Section "InputClass"
     Identifier "Touch"
     MatchIsTouchscreen "on"
     Option "TransformationMatrix" "0 1 0 -1 0 1 0 0 1"
   EndSection
   ```
5. Save and reboot. Try different matrix values if needed (there are 4 rotations: search "xorg TransformationMatrix rotate 90").

### "Google Sheets sync says 'Error: Credentials file not found'"
The JSON key file is missing or in the wrong place.
1. Confirm the file exists: `ls /home/pi/voting-system/credentials/`
2. You should see `google_service_account.json` listed.
3. If it's missing, repeat Step 12D.

### "Google Sheets sync fails with a permission error"
The spreadsheet hasn't been shared with the service account.
1. Open the JSON key file and copy the `client_email` value.
2. Open your Google Sheet → Share → add that email with Editor access.
3. Try syncing again.

### "Admin password not working"
Reset the password by running setup again:
```
cd /home/pi/voting-system
source venv/bin/activate
python app.py --setup
```
When prompted, enter a new password.

### "The voting service is not running"
Check what went wrong:
```
sudo journalctl -u voting-backend -n 50
```
This shows the last 50 log lines. Look for red error messages. Common causes:
- Virtual environment not found → confirm the venv folder exists at `/home/pi/voting-system/venv/`
- Database not found → run `python app.py --setup` again
- Port already in use → reboot the Pi

### "I accidentally changed something in config.py and now nothing works"
You can restore the original file from your USB drive backup, or re-copy the original `voting-system` folder from your Windows computer.

### "How do I read the log file?"
```
cat /home/pi/voting-system/logs/app.log
```
Or to see only the last 50 lines:
```
tail -n 50 /home/pi/voting-system/logs/app.log
```

---

## 19. Reference: What Each File Does

You do not need to understand or edit these files for normal use. This section is here for reference.

```
voting-system/
├── app.py              All web pages and the admin panel. This is the main program.
├── config.py           Settings: I2C address, timing, file paths. Edit this to adjust behaviour.
├── database.py         Manages the database where votes and cards are stored.
├── nfc_reader.py       Reads card taps from the PN532 HAT in the background.
├── sheets_sync.py      Sends results to Google Sheets.
├── requirements.txt    List of Python packages this app needs.
├── voting.db           The database file. Created automatically. Contains all votes.
├── .secret_key         A random security key. Created automatically. Do not delete or share.
│
├── templates/          HTML page templates (what you see in the browser)
│   ├── base.html           Common structure shared by all pages
│   ├── welcome.html        Blue "Tap Your Card" screen
│   ├── vote.html           The question and answer buttons
│   ├── thankyou.html       Results bar chart after voting
│   ├── closed.html         "Voting is Closed" screen
│   ├── error.html          Error messages (already voted, card not found, etc.)
│   └── admin/              Admin panel pages
│       ├── base.html           Navigation bar
│       ├── login.html          Password login
│       ├── dashboard.html      Home page with stats
│       ├── sessions.html       List of all voting sessions
│       ├── session_form.html   Create / edit a voting session
│       ├── cards.html          Enroll and manage RFID cards
│       ├── results.html        Live results chart
│       ├── export.html         CSV download and Sheets sync
│       └── settings.html       Google Sheets configuration
│
├── static/
│   ├── css/kiosk.css   Visual styling (large fonts, touch-friendly buttons)
│   └── js/kiosk.js     Touch screen hardening (prevents zoom, right-click, etc.)
│
├── credentials/
│   └── google_service_account.json   (You provide this in Step 12D)
│
├── systemd/            Auto-start configuration files for the Pi's service manager
│   ├── voting-backend.service    Starts the Python server on boot
│   └── voting-kiosk.service      Starts Chromium in kiosk mode on boot
│
└── logs/
    └── app.log         Log messages from the running server. Check here if something breaks.
```

---

## Quick Reference Card

Print this and keep it near the kiosk.

```
┌─────────────────────────────────────────────────────────┐
│           SCHOOL VOTING KIOSK — QUICK REFERENCE         │
├─────────────────────────────────────────────────────────┤
│ Admin panel:   http://127.0.0.1:5000/admin              │
│ Kiosk screen:  http://127.0.0.1:5000                    │
├─────────────────────────────────────────────────────────┤
│ MONDAY: Admin → Sessions → New Session                  │
│ FRIDAY: Admin → Export → Download CSV                   │
│         Admin → Export → Sync to Google Sheets          │
├─────────────────────────────────────────────────────────┤
│ ADD CARD:      Admin → Cards → tap card → Enroll        │
│ REMOVE CARD:   Admin → Cards → Deactivate               │
├─────────────────────────────────────────────────────────┤
│ If kiosk screen is stuck: unplug power, wait 10s,       │
│ plug back in. Wait 90 seconds.                          │
│                                                         │
│ If NFC not reading: check HAT is firmly seated on Pi.   │
└─────────────────────────────────────────────────────────┘
```
