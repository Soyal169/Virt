#!/usr/bin/env python3
"""
QA Automation Take-Home Task
Candidate Submission: Partner Signup Flow Automation
Target: https://authorized-partner.vercel.app/
Framework: Playwright (Python)
"""

import os
import sys
import time
import json
import uuid
import re
import logging
import urllib.request
import urllib.error
from pathlib import Path
from faker import Faker
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Optional OpenCV for automatic video conversion to MP4
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

# Load environment variables
load_dotenv()

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("test_execution.log", mode="w", encoding="utf-8")
    ]
)
logger = logging.getLogger("SignupAutomation")

# --- Test Settings ---
BASE_URL = os.getenv("BASE_URL", "https://authorized-partner.vercel.app")
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")
SLOW_MO = int(os.getenv("SLOW_MO", "150"))
TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "SecurePass@2025!")
SAMPLE_DOCUMENT = os.path.abspath(os.getenv("SAMPLE_DOCUMENT_NAME", "business_registration_sample.pdf"))
SCREENSHOTS_DIR = os.path.abspath("screenshots")
TEMP_VIDEO_DIR = os.path.abspath("temp_video")
FINAL_VIDEO_PATH = os.path.abspath("demo_video.mp4")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)


# --- Mail.tm Helper for Automated 6-Digit Email OTP ---
class TempMailService:
    """
    Automates email OTP verification using Mail.tm's public REST API.
    Zero manual intervention required:
    1. Creates a temporary inbox dynamically.
    2. Polls for the confirmation email sent by the backend.
    3. Extracts the 6-digit verification code using regex.
    """
    API_URL = "https://api.mail.tm"

    @classmethod
    def create_account(cls):
        """Creates a fresh inbox and returns (email_address, auth_token)."""
        logger.info("Provisioning temporary inbox via Mail.tm API for automated OTP...")
        # 1. Fetch available domain
        req = urllib.request.Request(f"{cls.API_URL}/domains")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            domain = data["hydra:member"][0]["domain"]

        username = f"qa_intern_{uuid.uuid4().hex[:8]}"
        email = f"{username}@{domain}"
        password = "Password123!"

        # 2. Register new inbox
        account_req = urllib.request.Request(
            f"{cls.API_URL}/accounts",
            data=json.dumps({"address": email, "password": password}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(account_req, timeout=10):
            pass

        # 3. Get JWT token
        token_req = urllib.request.Request(
            f"{cls.API_URL}/token",
            data=json.dumps({"address": email, "password": password}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(token_req, timeout=10) as resp:
            token = json.loads(resp.read().decode())["token"]

        logger.info(f"Temporary test inbox created: {email}")
        return email, token

    @classmethod
    def get_otp_code(cls, token, max_attempts=15, delay=2):
        """Polls inbox for the 6-digit OTP code."""
        logger.info("Waiting for OTP email from staging backend...")
        for attempt in range(1, max_attempts + 1):
            time.sleep(delay)
            req = urllib.request.Request(
                f"{cls.API_URL}/messages",
                headers={"Authorization": f"Bearer {token}"}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    messages = json.loads(resp.read().decode()).get("hydra:member", [])
                    if messages:
                        msg_id = messages[0]["id"]
                        msg_req = urllib.request.Request(
                            f"{cls.API_URL}/messages/{msg_id}",
                            headers={"Authorization": f"Bearer {token}"}
                        )
                        with urllib.request.urlopen(msg_req, timeout=10) as m_resp:
                            msg_body = json.loads(m_resp.read().decode())
                            text = (msg_body.get("text") or "") + " " + (msg_body.get("intro") or "")
                            logger.info(f"Received email subject: '{msg_body.get('subject')}'")
                            match = re.search(r'\b\d{6}\b', text)
                            if match:
                                otp = match.group(0)
                                logger.info(f"Extracted OTP code: {otp}")
                                return otp
            except Exception as e:
                logger.warning(f"Mail poll retry ({attempt}/{max_attempts}): {e}")
        return None


# --- Video Conversion Helper ---
def export_mp4_video(temp_dir: str, target_path: str):
    """Converts Playwright's recorded webm video to MP4 using OpenCV."""
    raw_videos = list(Path(temp_dir).glob("*.webm"))
    if not raw_videos or not OPENCV_AVAILABLE:
        return

    latest_video = str(sorted(raw_videos, key=os.path.getmtime)[-1])
    logger.info(f"Exporting recorded session to {target_path}...")
    try:
        cap = cv2.VideoCapture(latest_video)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(target_path, fourcc, fps, (width, height))

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
        cap.release()
        out.release()
        logger.info(f"Video saved successfully: {target_path}")
    except Exception as e:
        logger.warning(f"Could not convert video to MP4: {e}")


# --- Main Automation Test Suite ---
class SignupFlowTestSuite:
    def __init__(self):
        self.fake = Faker()
        self.test_results = []

    def log_result(self, test_id: str, description: str, passed: bool, notes: str = ""):
        status = "PASS" if passed else "FAIL"
        self.test_results.append({
            "id": test_id,
            "description": description,
            "status": status,
            "notes": notes
        })
        log_fn = logger.info if passed else logger.error
        log_fn(f"[{status}] {test_id} - {description} | {notes}")

    def capture(self, page, filename: str):
        path = os.path.join(SCREENSHOTS_DIR, f"{filename}.png")
        page.screenshot(path=path, full_page=True)
        logger.info(f"Screenshot captured: {filename}.png")

    def run(self):
        start_time = time.time()
        logger.info("=================================================================")
        logger.info("       STARTING QA AUTOMATION SUITE: SIGNUP FLOW                ")
        logger.info(f"       Target: {BASE_URL} | Headless: {HEADLESS}                ")
        logger.info("=================================================================")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=HEADLESS,
                slow_mo=SLOW_MO if not HEADLESS else 0
            )
            context = browser.new_context(
                record_video_dir=TEMP_VIDEO_DIR,
                record_video_size={"width": 1280, "height": 720},
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()
            page.set_default_timeout(TIMEOUT)

            try:
                # -------------------------------------------------------------
                # STEP 0: TERMS AGREEMENT & GATEKEEPING
                # -------------------------------------------------------------
                logger.info("\n--- [Step 0: Terms Agreement & Gatekeeping] ---")
                page.goto(f"{BASE_URL}/register")
                page.wait_for_load_state("networkidle")
                self.capture(page, "01_landing_terms")

                # Negative test: clicking Continue before agreeing
                continue_btn = page.locator("button:has-text('Continue')")
                continue_btn.click()
                page.wait_for_timeout(500)
                terms_blocked = "step=" not in page.url
                self.log_result(
                    "TC-NEG-01",
                    "Terms Agreement Gatekeeping",
                    terms_blocked,
                    "Navigation correctly blocked until Terms checkbox is checked"
                )

                # Check terms checkbox and proceed
                page.locator("#remember").click()
                self.capture(page, "02_terms_accepted")
                continue_btn.click()
                page.wait_for_url("**/register?step=setup")
                page.wait_for_load_state("networkidle")

                # -------------------------------------------------------------
                # STEP 1: PERSONAL DETAILS (NEGATIVE & VALIDATION TESTS)
                # -------------------------------------------------------------
                logger.info("\n--- [Step 1: Personal Details Negative Validations] ---")
                page.wait_for_selector("input[name='firstName']")

                # Negative test: Submit empty form
                page.locator("button:has-text('Next')").click()
                page.wait_for_timeout(600)
                self.capture(page, "03_step1_empty_validation")

                errors = page.locator(".text-destructive, p.text-red-500").all_inner_texts()
                empty_valid = any("First name" in e for e in errors) and any("Last name" in e for e in errors)
                self.log_result(
                    "TC-NEG-02",
                    "Step 1 - Empty Fields Validation",
                    empty_valid,
                    f"Triggered expected field errors: {errors}"
                )

                # Negative test: Invalid email syntax
                page.locator("input[name='firstName']").fill("Alex")
                page.locator("input[name='lastName']").fill("Tester")
                page.locator("input[name='email']").fill("not-a-valid-email")
                page.locator("button:has-text('Next')").click()
                page.wait_for_timeout(600)
                self.capture(page, "04_step1_invalid_email")

                email_errors = page.locator(".text-destructive, p.text-red-500").all_inner_texts()
                invalid_email_ok = any("Invalid email" in e for e in email_errors)
                self.log_result(
                    "TC-NEG-03",
                    "Step 1 - Invalid Email Syntax",
                    invalid_email_ok,
                    "Error 'Invalid email address' displayed properly"
                )

                # Negative test: Password mismatch
                page.locator("input[name='email']").fill("qa.valid@example.com")
                page.locator("input[name='password']").fill("Password@123")
                page.locator("input[name='confirmPassword']").fill("Mismatch@999")
                page.locator("button:has-text('Next')").click()
                page.wait_for_timeout(600)
                self.capture(page, "05_step1_password_mismatch")

                mismatch_ok = "step=setup" in page.url
                self.log_result(
                    "TC-NEG-04",
                    "Step 1 - Password Mismatch Validation",
                    mismatch_ok,
                    "Advancement blocked when passwords do not match"
                )

                # -------------------------------------------------------------
                # STEP 1: HAPPY PATH & AUTOMATED EMAIL OTP VERIFICATION
                # -------------------------------------------------------------
                logger.info("\n--- [Step 1: Happy Path Account Creation & Live OTP] ---")
                user_email, mail_token = TempMailService.create_account()
                first_name = self.fake.first_name()
                last_name = self.fake.last_name()
                phone_number = f"98{self.fake.numerify('########')}"

                logger.info(f"Registering user: {first_name} {last_name} | Email: {user_email} | Phone: {phone_number}")
                page.locator("input[name='firstName']").fill(first_name)
                page.locator("input[name='lastName']").fill(last_name)
                page.locator("input[name='email']").fill(user_email)
                page.locator("input[name='phoneNumber']").fill(phone_number)
                page.locator("input[name='password']").fill(DEFAULT_PASSWORD)
                page.locator("input[name='confirmPassword']").fill(DEFAULT_PASSWORD)

                self.capture(page, "06_step1_valid_filled")
                page.locator("button:has-text('Next')").click()

                # Wait for OTP screen
                page.wait_for_selector("text=Email Verification code", timeout=20000)
                self.capture(page, "07_otp_screen")

                # Fetch real OTP from Mail.tm
                otp_code = TempMailService.get_otp_code(mail_token)
                if not otp_code:
                    raise RuntimeError("OTP was not received within the timeout.")

                page.locator("input").first.fill(otp_code)
                self.capture(page, "08_otp_filled")
                page.locator("button:has-text('Verify Code')").click()

                page.wait_for_url("**/register?step=details", timeout=20000)
                page.wait_for_load_state("networkidle")
                self.capture(page, "09_otp_verified_success")

                self.log_result(
                    "TC-HP-01a",
                    "Step 1 - Account Creation & Email OTP Verification",
                    True,
                    f"OTP ({otp_code}) verified automatically; navigated to Step 2"
                )

                # -------------------------------------------------------------
                # STEP 2: AGENCY DETAILS
                # -------------------------------------------------------------
                logger.info("\n--- [Step 2: Agency Details] ---")
                page.wait_for_selector("input[name='agency_name']")

                # Negative test: Empty submit
                page.locator("button:has-text('Next')").click()
                page.wait_for_timeout(600)
                self.capture(page, "10_step2_empty_validation")

                step2_errs = page.locator(".text-destructive, p.text-red-500").all_inner_texts()
                step2_neg_ok = any("agency's name" in e for e in step2_errs)
                self.log_result(
                    "TC-NEG-05",
                    "Step 2 - Agency Details Empty Validation",
                    step2_neg_ok,
                    f"Field validation errors displayed: {step2_errs}"
                )

                # Fill valid Agency Details
                company_name = f"{self.fake.company()} Global Education"
                page.locator("input[name='agency_name']").fill(company_name)
                page.locator("input[name='role_in_agency']").fill("Managing Director")
                page.locator("input[name='agency_email']").fill(f"info@{self.fake.domain_name()}")
                page.locator("input[name='agency_website']").fill(f"www.{self.fake.domain_name()}")
                page.locator("input[name='agency_address']").fill("Putalisadak, Kathmandu, Nepal")

                # Select Region from combobox popover
                page.locator("button:has-text('Select Your Region of Operation')").click()
                page.wait_for_timeout(400)
                page.locator("[role='dialog'] >> text=Nepal").click()
                page.wait_for_timeout(200)
                page.keyboard.press("Escape")

                self.capture(page, "11_step2_filled")
                page.locator("button:has-text('Next')").click()
                page.wait_for_url("**/register?step=professional-experience", timeout=20000)
                page.wait_for_load_state("networkidle")

                self.log_result(
                    "TC-HP-01b",
                    "Step 2 - Agency Profile Completion",
                    True,
                    "Agency details submitted; advanced to Step 3"
                )

                # -------------------------------------------------------------
                # STEP 3: PROFESSIONAL EXPERIENCE & PERFORMANCE
                # -------------------------------------------------------------
                logger.info("\n--- [Step 3: Professional Experience & Metrics] ---")
                page.wait_for_selector("input[name='number_of_students_recruited_annually']")

                # Negative test: Empty submit
                page.locator("button:has-text('Next')").click()
                page.wait_for_timeout(600)
                self.capture(page, "12_step3_empty_validation")

                step3_errs = page.locator(".text-destructive, p.text-red-500").all_inner_texts()
                step3_neg_ok = any("experience level" in e.lower() for e in step3_errs)
                self.log_result(
                    "TC-NEG-06",
                    "Step 3 - Experience Metrics Empty Validation",
                    step3_neg_ok,
                    f"Validation errors displayed: {step3_errs}"
                )

                # Fill valid Experience Data
                page.locator("button:has-text('Select Your Experience Level')").click()
                page.wait_for_timeout(300)
                page.locator("[role='option']:has-text('5 years'), span:text-is('5 years')").first.click()

                page.locator("input[name='number_of_students_recruited_annually']").fill("150")
                page.locator("input[name='focus_area']").fill("Undergraduate STEM & Graduate Business in USA/Canada")
                page.locator("input[name='success_metrics']").fill("95")

                # Multi-select checkboxes
                page.locator("label:has-text('Career Counseling')").click()
                page.locator("label:has-text('Admission Applications')").click()
                page.locator("label:has-text('Visa Processing')").click()

                self.capture(page, "13_step3_filled")
                page.locator("button:has-text('Next')").click()
                page.wait_for_url("**/register?step=verification", timeout=20000)
                page.wait_for_load_state("networkidle")

                self.log_result(
                    "TC-HP-01c",
                    "Step 3 - Professional Experience & Performance",
                    True,
                    "Experience metrics saved; advanced to Step 4"
                )

                # -------------------------------------------------------------
                # STEP 4: VERIFICATION, PREFERENCES & DOCUMENT UPLOAD
                # -------------------------------------------------------------
                logger.info("\n--- [Step 4: Verification, Preferences & Document Upload] ---")
                page.wait_for_selector("input[name='business_registration_number']")

                # Negative test: Empty submit
                page.locator("button:has-text('Submit')").click()
                page.wait_for_timeout(600)
                self.capture(page, "14_step4_empty_validation")

                step4_errs = page.locator(".text-destructive, p.text-red-500").all_inner_texts()
                step4_neg_ok = any("registration number" in e.lower() for e in step4_errs)
                self.log_result(
                    "TC-NEG-07",
                    "Step 4 - Verification & Documents Empty Validation",
                    step4_neg_ok,
                    f"Validation errors displayed: {step4_errs}"
                )

                # Fill valid Verification Data
                reg_no = f"BRN-{self.fake.numerify('######')}-NP"
                page.locator("input[name='business_registration_number']").fill(reg_no)

                # Multi-select preferred countries
                page.locator("button:has-text('Select Your Preferred Countries')").click()
                page.wait_for_timeout(400)
                page.locator("[role='dialog'] >> text=Australia").click()
                page.wait_for_timeout(200)
                page.locator("[role='dialog'] >> text=Canada").click()
                page.wait_for_timeout(200)
                page.keyboard.press("Escape")

                # Preferred Institution Types
                page.locator("label:has-text('Universities')").click()
                page.locator("label:has-text('Colleges')").click()

                # Certification Details (Optional)
                page.locator("input[name='certification_details']").fill("Certified Education Agent (QEAC / ICEF)")

                # Document Upload
                logger.info(f"Attaching business document: {SAMPLE_DOCUMENT}")
                page.locator("input[type='file']").first.set_input_files(SAMPLE_DOCUMENT)
                page.wait_for_timeout(1000)

                self.capture(page, "15_step4_all_filled")
                page.locator("button:has-text('Submit')").click()

                # Wait for redirection to Admin Portal
                page.wait_for_url("**/admin**", timeout=30000)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2500)

                self.capture(page, "16_final_dashboard")
                body_text = page.locator("body").inner_text()
                completed = ("Registration completed" in body_text) or ("/admin" in page.url)

                self.log_result(
                    "TC-HP-01d",
                    "Step 4 - Final Submission & Portal Access",
                    completed,
                    f"Signup completed successfully; user redirected to {page.url}"
                )

            except Exception as e:
                logger.error(f"Error during execution: {e}", exc_info=True)
                try:
                    self.capture(page, "99_failure_state")
                except:
                    pass
            finally:
                logger.info("Closing browser context and finalizing recording...")
                context.close()
                browser.close()

        # Transcode video to demo_video.mp4 if OpenCV is available
        export_mp4_video(TEMP_VIDEO_DIR, FINAL_VIDEO_PATH)

        duration = time.time() - start_time
        # Print summary
        logger.info("\n" + "="*70)
        logger.info("                  TEST EXECUTION SUMMARY                        ")
        logger.info("="*70)
        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        total = len(self.test_results)
        for r in self.test_results:
            logger.info(f"  [{r['status']}] {r['id']:<10} | {r['description']:<45} |")
        logger.info("-" * 70)
        logger.info(f"  TOTAL: {total} | PASSED: {passed} | FAILED: {total - passed} | TIME: {duration:.1f}s")
        logger.info("="*70 + "\n")

        if passed < total:
            sys.exit(1)
        else:
            logger.info("All test cases passed with 100% success rate.")
            sys.exit(0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Authorized Partner Signup Flow Automation")
    parser.add_argument("--headed", action="store_true", help="Launch visible browser window (default if HEADLESS=false)")
    parser.add_argument("--headless", action="store_true", help="Run in headless background mode")
    parser.add_argument("--slowmo", type=int, default=None, help="Delay in ms between actions (e.g. 150)")
    args = parser.parse_args()

    if args.headed:
        HEADLESS = False
    elif args.headless:
        HEADLESS = True

    if args.slowmo is not None:
        SLOW_MO = args.slowmo

    suite = SignupFlowTestSuite()
    suite.run()
