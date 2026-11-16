# Partner Signup Flow - QA Automation & Execution Steps

This repository contains the automated test suite for the multi-step partner registration flow on **[Authorized Partner](https://authorized-partner.vercel.app/)**, developed using **Playwright (Python)** for the QA Automation take-home assignment.

The automation executes **100% autonomously with zero manual intervention**, handling form submissions across all signup pages, negative validations, dynamic test data generation, real-time email OTP verification, and document uploads.

---

## Deliverables & Project Structure

As requested in the submission instructions, all required deliverables are included and named clearly:

| File / Folder | Description |
|---|---|
| `signup_automation_script.py` | Main Playwright automation script covering negative tests and full happy path |
| `README_execution_steps.md` | Complete setup instructions, execution commands, environment details, and findings |
| `README.md` | Standard repository documentation and quick-start guide |
| `test_report.pdf` | Comprehensive QA test report with test cases table, metrics, findings, and screenshots |
| `demo_video.mp4` | Screen recording of the automated execution across all signup steps |
| `requirements.txt` | Pinned Python dependencies |
| `.env.example` | Template for environment configuration |
| `business_registration_sample.pdf` | Sample certificate document used for Step 4 file upload |
| `screenshots/` | Full-page screenshots captured at each step and validation state |

---

## Environment & Setup

- **Language:** Python `3.10.6` (Compatible with Python 3.9+)
- **Testing Framework:** Playwright for Python (`playwright==1.65.2`)
- **Browser:** Chromium (Playwright bundled build `1155`)
- **Operating System:** Windows 10/11 (Cross-platform compatible with macOS and Linux)
- **Key Libraries:**
  - `playwright`: Core browser automation engine
  - `faker`: Dynamic generation of realistic user and agency test data
  - `python-dotenv`: Environment configuration management
  - `opencv-python`: Session video export to MP4 format

---

## Prerequisites & Installation

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd <repository-folder>
```

### Step 2: Create and Activate Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment:
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate
```

### Step 3: Install Dependencies & Playwright Browser
```bash
pip install -r requirements.txt
playwright install chromium
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

---

## How to Run the Script

### 1. Default Run (Headed Mode - Browser Opens Visibly)
By default, running the script opens a visible Chromium browser window on your screen with a smooth pacing delay (`SLOW_MO=150ms`) so you can watch each step execute live:

```bash
python signup_automation_script.py
```

### 2. Headless Mode (Background Execution)
If you prefer running silently without opening the browser window (e.g., in CI/CD):

```bash
python signup_automation_script.py --headless
```

### 3. Adjusting Execution Speed
You can adjust the speed of the visible browser execution by specifying `--slowmo` (in milliseconds):

```bash
python signup_automation_script.py --slowmo 300
```

---

## Test Data & Accounts Used

1. **User Personal Details (Step 1):**
   - Dynamically generated using `Faker` (randomized First Name, Last Name, Phone Number).
   - Password: `SecurePass@2025!` (configurable in `.env`).
2. **Automated Real-Time Email OTP (No Manual Intervention):**
   - During Step 1, the backend (`https://stage.cloudedu.com.au/api/tempuser/`) sends a 6-digit verification code to the user's email.
   - The script creates a temporary disposable inbox dynamically using the **Mail.tm API** (`https://api.mail.tm`).
   - The script polls the inbox via authenticated API requests, extracts the 6-digit code via regex (`\b\d{6}\b`) from the incoming email within 2–4 seconds, and automatically fills the verification code input.
3. **Agency Profile (Step 2):**
   - Unique agency company name, role ("Managing Director"), contact email, website, address ("Putalisadak, Kathmandu, Nepal"), and Region of Operation ("Nepal").
4. **Professional Experience (Step 3):**
   - Experience Level: "5 years"
   - Students Recruited: 150
   - Focus Area: "Undergraduate STEM & Graduate Business in USA/Canada"
   - Success Rate: 95%
   - Services: Career Counseling, Admission Applications, Visa Processing.
5. **Verification & Documents (Step 4):**
   - Business Registration Number: dynamic (`BRN-XXXXXX-NP`)
   - Preferred Countries: "Australia", "Canada"
   - Preferred Institution Types: "Universities", "Colleges"
   - Uploaded Document: `business_registration_sample.pdf`

---

## Test Scenarios & Coverage Summary

| Test ID | Category | Target | Description | Status |
|---|---|---|---|---|
| **TC-NEG-01** | Negative | Step 0 | Asserts Continue button cannot proceed without accepting Terms & Conditions. | **PASS** |
| **TC-NEG-02** | Negative | Step 1 | Asserts validation errors when submitting empty personal details form. | **PASS** |
| **TC-NEG-03** | Negative | Step 1 | Asserts error message when malformed email syntax is entered. | **PASS** |
| **TC-NEG-04** | Negative | Step 1 | Asserts advancement is blocked when passwords do not match. | **PASS** |
| **TC-HP-01a** | Happy Path | Step 1 | Submits valid user data, retrieves live email OTP via Mail.tm API, enters 6-digit code. | **PASS** |
| **TC-NEG-05** | Negative | Step 2 | Asserts field errors when submitting empty agency details. | **PASS** |
| **TC-HP-01b** | Happy Path | Step 2 | Fills valid agency details and selects Region of Operation from popover combobox. | **PASS** |
| **TC-NEG-06** | Negative | Step 3 | Asserts validation messages when submitting empty experience metrics. | **PASS** |
| **TC-HP-01c** | Happy Path | Step 3 | Fills experience level, recruit count, focus area, success rate, and services. | **PASS** |
| **TC-NEG-07** | Negative | Step 4 | Asserts validation messages when submitting without registration number or document. | **PASS** |
| **TC-HP-01d** | Happy Path | Step 4 | Enters BRN, selects countries & institutions, uploads PDF document, asserts redirect to Admin Portal. | **PASS** |

---

## QA Observations & Platform Bugs Discovered

1. **Backend IP Rate Limiting (HTTP 429):**
   - The staging backend (`stage.cloudedu.com.au`) enforces Django REST Framework rate throttling returning `HTTP 429 (Too many requests)` with a `retry-after: 600` header (10-minute cooldown) when multiple tempuser registrations occur in short succession from the same IP.
   - The script performs a single clean, end-to-end registration per test run to respect this throttle window.
2. **UI Typographical Defect:**
   - In Step 3 (Professional Experience), the checkbox label for test preparation contains a typo: `"Test Prepration"` instead of `"Test Preparation"`.
3. **Session Persistence:**
   - Once Step 1 OTP is verified, an authentication cookie is established. If the user logs in later, the application smartly routes them directly to their pending registration step.
4. **Dynamic Combobox Popovers:**
   - The Region and Country dropdowns render floating popover dialogs (`role="dialog"`). The script explicitly selects target options and dismisses the popover using keyboard escape to avoid overlay blocking.
