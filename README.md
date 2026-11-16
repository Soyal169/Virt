# Authorized Partner - Signup Flow QA Automation

This repository contains an end-to-end QA automation test suite for the multi-step partner registration flow on **[Authorized Partner](https://authorized-partner.vercel.app/)**, built using **Playwright (Python)**.

The suite achieves **100% automated execution with zero manual intervention**, covering client-side and server-side validation, multi-step navigation, real-time email OTP verification, file uploads, and post-signup dashboard verification.

---

## Deliverables Summary

| File / Directory | Purpose |
|---|---|
| `signup_automation_script.py` | Complete Playwright Python automation script covering negative tests and full happy path |
| `README_execution_steps.md` | Detailed execution steps, environment specifications, and test data details (as requested in submission prompt) |
| `README.md` | Setup instructions, architecture overview, and quick-start guide |
| `requirements.txt` | Pinned production dependencies |
| `test_report.pdf` | Comprehensive execution report with metrics, test cases table, analysis, and embedded screenshots |
| `demo_video.mp4` | High-definition MP4 recording of the full automated test execution |
| `.gitignore` | Excludes secrets, virtual environments, cache, and temporary recording files |
| `.env.example` | Template for environment configuration |
| `business_registration_sample.pdf` | Sample PDF document used for Step 4 document verification upload |
| `screenshots/` | High-resolution screenshots captured at every step, validation state, and completion |

---

## Environment & Prerequisites

The test suite was developed, verified, and executed under the following environment:

- **Operating System:** Windows 10/11 (x86_64) (Cross-platform compatible with macOS and Linux)
- **Python Version:** `3.10.6` (Compatible with Python 3.9+)
- **Playwright Version:** `1.65.2`
- **Browser Tested:** Chromium (Playwright bundled build `1155`)
- **OpenCV Version:** `4.9.0.80` (Used for pure-Python WebM-to-MP4 video transcoding)
- **ReportLab Version:** `5.1.0` (Used for PDF report compilation)
- **Faker Version:** `40.54.0` (Used for dynamic unique test data synthesis)

---

## Architecture & Automation Highlights

### 1. Automated Real-Time Email OTP Verification (Zero Manual Intervention)
During Step 1, the backend (`https://stage.cloudedu.com.au/api/tempuser/`) sends a 6-digit verification code to the registered email address. Rather than requiring human intervention or hardcoded mocks, the script:
- Dynamically provisions a disposable test inbox via the **Mail.tm REST API**.
- Submits the temporary inbox address in the signup form.
- Polls the inbox via authenticated API requests with exponential backoff.
- Extracts the 6-digit OTP code (`\b\d{6}\b`) from the message body within 2–4 seconds.
- Automatically types the OTP into the verification form and submits.

### 2. Multi-Step Form State Machine Coverage
The registration flow consists of 5 distinct phases, all handled autonomously:
1. **Terms Agreement (Step 0):** Gatekeeping terms checkbox before unlocking registration.
2. **Account Setup & OTP (Step 1):** Personal info (`firstName`, `lastName`, `email`, `phoneNumber`, `password`, `confirmPassword`) followed by email OTP verification.
3. **Agency Details (Step 2):** Company details, role, email, website, address, and interactive region dropdown selection.
4. **Professional Experience (Step 3):** Experience level dropdown, annual recruit numbers, target focus area, success percentage, and multi-service checkboxes.
5. **Verification & Document Upload (Step 4):** Business registration number, target countries, institution preferences, certification text, and PDF document attachment.
6. **Admin Dashboard Transition:** Asserting successful account creation, profile redirection, and dashboard access.

### 3. Reliable Locators & Explicit Synchronization
- Uses semantic role and attribute locators (`page.locator("input[name='...']")`, `page.locator("button:has-text('...')")`, `[role='combobox']`, `[role='dialog']`).
- Replaces brittle sleep timers with explicit Playwright wait conditions: `wait_for_selector`, `wait_for_url`, and `wait_for_load_state("networkidle")`.

### 4. Pure-Python Video Recording & Transcoding
- Playwright records full video during test execution via `record_video_dir`.
- OpenCV dynamically transcodes the raw `.webm` stream into a standardized H.264 compatible `demo_video.mp4` without requiring external `ffmpeg` binaries in the system path.

---

## Installation & Setup

### Step 1: Clone Repository & Create Virtual Environment

```bash
# Clone the repository
git clone <repository-url>
cd <repository-folder>

# Create clean virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate
```

### Step 2: Install Dependencies & Playwright Browsers

```bash
# Install pinned dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### Step 3: Configure Environment Variables

Copy the example configuration:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Default `.env` contents:
```env
BASE_URL=https://authorized-partner.vercel.app
HEADLESS=false
SLOW_MO=150
BROWSER_TIMEOUT=30000
DEFAULT_PASSWORD=SecurePass@2025!
SAMPLE_DOCUMENT_NAME=business_registration_sample.pdf
```

---

## How to Run the Script

### 1. Visible (Headed) Execution (Default)
By default, running the script opens a visible Chromium browser window on your screen and steps through each phase with a slight pacing delay (`SLOW_MO=150ms`) so every interaction is easy to observe live:

```bash
python signup_automation_script.py
```
Or explicitly:
```bash
python signup_automation_script.py --headed
```

### 2. Headless Mode (Background Execution)
To run silently in the background (e.g. in CI/CD pipelines):

```bash
python signup_automation_script.py --headless
```

### 3. Custom Slow Motion Pacing
You can adjust the speed of the visible browser execution (in milliseconds):

```bash
python signup_automation_script.py --slowmo 300
```

---

## Test Cases & Validation Coverage

| Test ID | Test Category | Target Step | Description & Assertion | Status |
|---|---|---|---|---|
| **TC-NEG-01** | Negative | Step 0 | Validates that clicking "Continue" without accepting Terms & Conditions is blocked. | **PASS** |
| **TC-NEG-02** | Negative | Step 1 | Validates required field messages ("First name must be at least 2 characters", "Last name...", "Invalid email"). | **PASS** |
| **TC-NEG-03** | Negative | Step 1 | Validates that malformed email format triggers "Invalid email address" and halts submission. | **PASS** |
| **TC-NEG-04** | Negative | Step 1 | Validates that mismatched passwords prevent submission. | **PASS** |
| **TC-HP-01a**| Happy Path | Step 1 | Generates unique user details, receives live email OTP via Mail.tm API, enters 6-digit code, advances to Step 2. | **PASS** |
| **TC-NEG-05** | Negative | Step 2 | Validates required fields on Agency Details (Agency Name, Role, Email, Website, Address, Region). | **PASS** |
| **TC-HP-01b**| Happy Path | Step 2 | Populates valid agency data and selects region ("Nepal") from popover dropdown. | **PASS** |
| **TC-NEG-06** | Negative | Step 3 | Validates required fields on Professional Experience (Experience Level, Recruits, Focus, Services). | **PASS** |
| **TC-HP-01c**| Happy Path | Step 3 | Selects experience level ("5 years"), sets recruitment metric (175), selects services, advances to Step 4. | **PASS** |
| **TC-NEG-07** | Negative | Step 4 | Validates required fields on Verification (Registration Number, Countries, Institution Types, Document Upload). | **PASS** |
| **TC-HP-01d**| Happy Path | Step 4 | Enters BRN, selects preferred countries & institution types, uploads sample PDF document, submits form, and asserts redirection to `/admin/profile`. | **PASS** |

---

## Platform Observations & QA Findings

During deep live exploratory testing and automation execution, the following platform behaviors were identified:

1. **Backend IP Rate Limiting (HTTP 429):**
   - The staging endpoint (`https://stage.cloudedu.com.au/api/tempuser/`) enforces strict IP-based rate throttling (`retry-after: 600`).
   - If multiple accounts are created from the same public IP within a short window, the server returns `429 Too Many Requests`. The script executes a single clean, end-to-end account registration per suite run to respect this throttle.
2. **UI Typographical Defect:**
   - On Step 3 (Professional Experience), the checkbox label for test preparation contains a typo: `"Test Prepration"` instead of `"Test Preparation"`.
3. **Session Resumption:**
   - Once Step 1 OTP is verified, an authenticated session cookie (`auth-token`) is established. If a user logs out and logs back in before finishing all steps, the system intelligently resumes the onboarding wizard at the exact uncompleted step.
4. **Combobox Popover Behavior:**
   - The "Region of Operation" (Step 2) and "Preferred Countries" (Step 4) comboboxes render dynamic popovers (`role="dialog"`). The script explicitly interacts with search filters and popover options, using escape keys to cleanly dismiss overlays.

---

## Test Execution Summary Sample Output

```text
======================================================================
                   TEST EXECUTION SUMMARY                       
======================================================================
  [PASS] TC-NEG-01  | Terms Agreement Gatekeeping              |
  [PASS] TC-NEG-02  | Step 1 - Empty Fields Validation         |
  [PASS] TC-NEG-03  | Step 1 - Invalid Email Syntax            |
  [PASS] TC-NEG-04  | Step 1 - Password Mismatch               |
  [PASS] TC-HP-01a  | Step 1 - Account Creation & Email OTP Verification |
  [PASS] TC-NEG-05  | Step 2 - Agency Details Empty Validation |
  [PASS] TC-HP-01b  | Step 2 - Agency Profile Completion       |
  [PASS] TC-NEG-06  | Step 3 - Experience Metrics Empty Validation |
  [PASS] TC-HP-01c  | Step 3 - Professional Experience & Performance |
  [PASS] TC-NEG-07  | Step 4 - Verification & Documents Empty Validation |
  [PASS] TC-HP-01d  | Step 4 - Final Submission & Portal Access |
----------------------------------------------------------------------
  TOTAL: 11 | PASSED: 11 | FAILED: 0 | TIME: 48.0s
======================================================================
All test cases passed successfully with 100% pass rate.
```

---

## Author & Verification

- **Task:** QA Automation Take-Home Task
- **Target URL:** `https://authorized-partner.vercel.app/`
- **Automation Engineer:** QA Automation Candidate
- **Verification Status:** Fully automated, verified end-to-end with real browser execution, video export, and PDF reporting.
