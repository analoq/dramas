"""Script that sends an email with content from stdin.  Used for alerts."""
from os import environ
import sys

from dotenv import load_dotenv

from email_client import EmailClient

load_dotenv()

def main():
    """Main program"""
    email = EmailClient(
        email_account=environ["EMAIL_ACCOUNT"],
        email_key=environ["EMAIL_ACCOUNT_KEY"]
    )
    email.send(
        to_email=environ["ALERT_EMAIL"],
        subject='DTMaaS System Alert',
        content=sys.stdin.read()
    )

if __name__ == "__main__":
    main()
