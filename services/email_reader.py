import imaplib
import email
import re
import os
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class EmailVerificationReader:
    def __init__(self):
        self.username = os.environ.get("GMAIL_USER")
        self.app_password = os.environ.get("GMAIL_APP_PASS")
        self.imap_server = "imap.gmail.com"
        self.mail = None

    def connect(self):
        if not self.username or not self.app_password:
            logger.error("Gmail credentials missing in environment variables.")
            return False
        
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.username, self.app_password)
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Gmail: {e}")
            return False

    def close(self):
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except Exception:
                pass

    def extract_pin_from_body(self, html_content: str) -> str | None:
        """Attempts to extract a verification code from email body."""
        soup = BeautifulSoup(html_content, "lxml")
        text = soup.get_text()
        
        # Look for 6 digit codes commonly used by SF
        match = re.search(r'\b(\d{6})\b', text)
        if match:
            return match.group(1)
            
        return None

    def fetch_latest_verification_code(self, from_email: str = None) -> str | None:
        """Fetches the latest verification code."""
        if not self.connect():
            return None

        try:
            self.mail.select("inbox")
            search_criteria = "ALL"
            if from_email:
                search_criteria = f'(FROM "{from_email}")'

            status, messages = self.mail.search(None, search_criteria)
            if status != "OK":
                return None

            email_ids = messages[0].split()
            if not email_ids:
                return None

            # Get the latest email
            latest_email_id = email_ids[-1]
            status, msg_data = self.mail.fetch(latest_email_id, '(RFC822)')
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/html" or part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                code = self.extract_pin_from_body(body)
                                if code:
                                    return code
                    else:
                        body = msg.get_payload(decode=True).decode()
                        return self.extract_pin_from_body(body)
            
        except Exception as e:
            logger.error(f"Error fetching email: {e}")
        finally:
            self.close()
            
        return None
