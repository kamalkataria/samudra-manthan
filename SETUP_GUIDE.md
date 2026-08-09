# 🌊 Samudra Manthan: Beginner's Setup Guide

Welcome! Because this app processes and deletes your emails, it is designed to run entirely on your local computer. This keeps your data **100% private**—no third-party servers will ever see your inbox.

If you have never used Python or a terminal before, follow these steps exactly. You will be up and running in about 10 minutes.

---

## 🛠️ 1. Install Python & PIP

You need **Python 3.10 or higher** installed on your computer.

1. Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest version.
2. Open the installer. 
> **⚠️ CRITICAL STEP FOR WINDOWS:** At the very bottom of the installer window, check the box that says **"Add Python to PATH"** before clicking Install. If you skip this, your terminal will not recognize Python commands.

3. Verify your installation by opening your terminal (Command Prompt on Windows, Terminal on Mac) and running:
   ```bash
   python --version
   ```
   *(On Mac/Linux, if `python` doesn't work, use `python3`).*

4. Ensure your Python package manager (`pip`) is ready and updated:
   ```bash
   python -m pip install --upgrade pip
   ```

---

## 📥 2. Download the Project

1. At the top of this GitHub page, click the green **Code** button and select **Download ZIP**.
2. Extract the ZIP file into a folder on your computer (for example, on your Desktop).
3. Open your terminal and use the `cd` (change directory) command to navigate inside that folder:
   ```bash
   cd Desktop/samudra-manthan-main
   ```

---

## 🫧 3. Set Up Virtual Environment (VENV)

A virtual environment is an isolated "bubble" on your computer. It keeps all required packages safely locked inside the project folder without affecting the rest of your system.

1. **Create the virtual environment:**
   ```bash
   python -m venv .venv
   ```
   *(This creates a hidden folder named `.venv`. It takes a few seconds and will not output any text).*

2. **Activate the virtual environment:**
   * **Windows:**
     ```cmd
     .venv\Scripts\activate
     ```
   * **Mac / Linux:**
     ```bash
     source .venv/bin/activate
     ```
   *(You will know it worked when `(.venv)` appears at the start of your terminal prompt).*

3. **Install project dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🔑 4. Google Credentials Setup

Because the app can permanently delete emails, Google requires it to run on your own personal "developer" credentials. This ensures no third party ever gains access to your inbox.

### Step-by-Step Credentials Generation:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and sign in with your Gmail account.
2. Click the **Select a project** dropdown at the top left → **New Project**. Name it `samudra-manthan` and click **Create**.
3. In the top search bar, search for **Gmail API**, click the top result, and click **Enable**.
4. On the left sidebar, click **OAuth consent screen**.
5. Select **External** and click **Create**.
6. Fill in the required fields:
   * **App name:** `Samudra Manthan`
   * **User support email:** (Select your Gmail)
   * **Developer contact information:** (Type your email)
7. Click **Save and Continue** until you reach the **Test users** page.
> **⚠️ CRITICAL STEP:** On the **Test users** page, click **+ Add Users** and type your exact Gmail address. If you skip this, Google will block you from logging in. Click **Save and Continue**.

8. On the left sidebar, click **Credentials**.
9. Click **+ Create Credentials** at the top → **OAuth client ID**.
10. Under "Application type", select **Desktop app**, name it `Samudra Client`, and click **Create**.
11. On the confirmation popup, click **Download JSON**.

### Place the Credentials File:
1. Find the downloaded file on your computer and rename it to exactly **`credentials.json`**.
2. Move this file into the **`config/`** directory inside your `samudra-manthan-main` project folder.

---

## 🚀 5. Run the Application

Make sure your virtual environment `(.venv)` is activated, then run:

```bash
python -m samudra_manthan
```

Select **Option 1 (Login with Google)** to authenticate and start cleaning your inbox!

---

## 📅 Everyday Use Guide

Once the one-time setup is complete, running the app on any future day requires only these quick commands:

1. Open terminal and navigate to project folder:
   ```bash
   cd Desktop/samudra-manthan-main
   ```
2. Activate virtual environment:
   * **Windows:**
     ```cmd
     .venv\Scripts\activate
     ```
   * **Mac / Linux:**
     ```bash
     source .venv/bin/activate
     ```
3. Launch the app:
   ```bash
   python -m samudra_manthan
   ```
