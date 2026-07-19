# WhatsApp Lead Dispatcher - Sooftcode

A modern, desktop-based GUI application built in Python using **CustomTkinter** to send bulk personalized WhatsApp messages to leads using the official **WhatsApp Business Cloud API**. 

The app features a multi-threaded architecture to ensure smooth UI performance, automatic number formatting, lead validation, duplicate detection, scheduling, customizable message templates, attachments support (images, PDFs, catalogs), and exportable campaign reports.

---

## Key Features

* **Modern GUI Layout**: Sidebar navigation, Light/Dark appearance mode, connection status tracking, and a live stats dashboard.
* **Smart Lead Importer**: Accepts CSV & Excel (`.xlsx`, `.xls`) files. Features automatic header mapping, Indian phone number format normalization, duplicate contact suppression, and validation error warnings.
* **Template Builder**: Save, load, edit, and delete templates in a local JSON storage. Supports dynamic personalization variables: `{{name}}`, `{{company}}`, `{{phone}}`, `{{email}}`.
* **Personalized Live Preview**: Instantly preview how the message will look for a selected lead as you draft your template.
* **Attachments Support**: Attach brochures, catalogs, images (`.png`, `.jpg`, `.jpeg`), or documents (`.pdf`). Local files are automatically uploaded to Meta servers once per campaign.
* **Campaign Scheduling**: Delay campaign execution to a specific date and time in the future.
* **Responsive Dispatch Controls**:
  * Set a configurable interval delay (3–15 seconds) between messages.
  * Pause, resume, or abort campaign sending at any time.
  * Auto-save campaign progress to Excel after every dispatch.
  * Completed campaigns play a system notification sound.
* **Reliable API Execution**: Built-in automatic retries (up to 3 times) for network timeouts, connection drops, and API rate limits (HTTP 429).
* **Comprehensive Logs**: Saves chronological activity records to a daily log file, displays logs live on-screen, and supports exporting logs to Excel.

---

## Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.12+** installed on your system.

### 2. Install Dependencies
Open your command line in the project folder and install the required modules:
```bash
pip install -r requirements.txt
```

### 3. WhatsApp Business Cloud API Configuration
You need to configure your Meta WhatsApp Cloud API credentials. You can set them directly in the `.env` file in the project root, or modify them inside the application's **Settings** panel.

Create/edit the `.env` file to contain:
```env
ACCESS_TOKEN=your_meta_system_user_or_temporary_token_here
PHONE_NUMBER_ID=your_whatsapp_phone_number_id_here
API_VERSION=v20.0
APP_THEME=System
SENDER_DELAY=5
RETRY_LIMIT=3
PLAY_SOUND=True
```

---

## Step-by-Step Usage Guide

### Step 1: Launch the Application
Start the program by running `main.py`:
```bash
python main.py
```

### Step 2: Preparing the Contacts Sheet (CSV or Excel)
Create a `.csv` or `.xlsx` spreadsheet for your leads. The application searches for headings using keywords and maps them automatically.

Your sheet should ideally include:
* **Name** (Mapped from *Name*, *Lead Name*, *Customer*) - *Required*
* **Phone Number** (Mapped from *Phone*, *Mobile*, *Contact*) - *Required*
* **Email** (Mapped from *Email*, *Mail*) - *Optional*
* **Company** (Mapped from *Company*, *Business*, *Org*) - *Optional*
* **Status** (Mapped from *Status*, *Delivery*) - *Optional*
* **Last Contact Date** (Mapped from *Date*, *Last Contact*) - *Optional*

*A pre-formatted sample file named `test_leads.csv` is provided in the project directory for testing.*

### Step 3: Load and Filter Leads
1. Select **Campaign Manager** from the sidebar.
2. Click **Import Leads File** and select your sheet.
3. Review the table rows:
   * Invalid numbers (e.g. letters, wrong length) are highlighted in **red** and unchecked.
   * Duplicate phone numbers are highlighted in **yellow** and unchecked.
   * Format-corrected numbers (e.g., stripping spaces, leading `0`s, prepending `91` for Indian numbers) display in the **Formatted Phone Number** column.
4. Check the boxes of the leads you wish to target (or check **Select All**). You can search for leads dynamically or filter them by company or delivery status using the top filters.

### Step 4: Drafting the Message
1. In the **Message Composer** on the right, you can load a saved template using the dropdown, or draft a new message.
2. Click the placeholder buttons (`+ Name`, `+ Company`, `+ Phone`, `+ Email`) to insert variables. They will be formatted as `{{name}}`, `{{company}}`, `{{phone}}`, or `{{email}}`.
3. Select any lead row in the table to see a **live compilation preview** in the **Message Preview** textbox.

### Step 5: Configure Attachments & Scheduling (Optional)
* **Attachments**: Check **Enable Attachment**, click **Browse File**, and select a PDF or image. The file size will be validated.
* **Scheduling**: Check **Schedule Future Run**, then enter the date (`YYYY-MM-DD`) and time (`HH:MM:SS`) you want the dispatch to start.

### Step 6: Send & Monitor Campaign
1. Set the delay interval slider (e.g. 5 seconds).
2. Click **Start Campaign**.
3. The progress bar will fill, and live log updates will print. You can click **Pause** to freeze sending and **Resume** to continue, or **Stop** to abort.
4. If the program terminates or is closed mid-campaign, you can retrieve the current progress backup file at `reports/active_campaign_progress.xlsx`.

---

## File Directory Structure

* `main.py`: Entry point and orchestrator linking GUI callbacks to backend services.
* `gui.py`: Defines layout widgets, frames, grid padding, styles, and themes.
* `whatsapp_api.py`: WhatsApp Cloud API client handling text/media dispatches, uploads, and retries.
* `excel_reader.py`: Lead sheet processing, duplicate filter, and validation logic.
* `template_manager.py`: JSON CRUD template builder and placeholder parser.
* `logger.py`: App logging, campaign histories, and report creation.
* `settings.py`: Environment variable and subdirectory organizer.
* `utils.py`: Phone validation, email check, and sound alert utils.
* `templates/`: Contains templates database (`templates.json`).
* `logs/`: Holds error log (`app.log`) and transaction CSV (`whatsapp_send_history.csv`).
* `reports/`: Stores progress backups and exported reports.
* `assets/`: Holds the company logo (`logo.png`).

---

## Troubleshooting & API Guidelines

* **Invalid OAuth Token (Error Code 190)**: Your Meta access token has expired or is invalid. Generate a permanent or new temporary access token in your Meta Developer Console and update it in settings.
* **Attachment Fails to Send**: Make sure your document/image file is not locked or open in another application. Images must be under 5MB for WhatsApp. PDFs can be up to 100MB.
* **Messages Sent but Not Received**: Check if the target phone number is registered on WhatsApp, and that the Meta Account has credit/payment method linked (Meta charges for conversations outside the trial limit).
* **Indian Phone Formatting**: Local 10-digit numbers starting with `6-9` are formatted by automatically prepending `91` (e.g., `9876543210` -> `919876543210`). Ensure other international numbers include their country code.
