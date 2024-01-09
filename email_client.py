"""Email client for handling sending and receiving emails"""
import base64
import logging
import re
import socket
from os import environ
from dataclasses import dataclass
from email import message_from_bytes
from email.message import Message, EmailMessage
from email.utils import parseaddr
from imaplib import IMAP4_SSL
from smtplib import SMTP_SSL 
from enum import Enum
from typing import Iterator, Union, Tuple, Optional

class RequestEmailValidationResult(Enum):
    """Validation results for a request email"""
    OK = 'OK'
    TOO_BIG = 'Email too large >1 MiB'
    NO_MIDI = 'No MIDI attached'

@dataclass
class RequestEmail:
    """Represents an emailed MIDI request and whether it has errors"""
    validation_result: RequestEmailValidationResult
    from_email: str
    to_email: str
    midi_name: Union[None, str]
    midi_data: Union[None, bytes]

class EmailClient:
    """Class for handling sending and receiving emails via Gmail"""

    SMTP_HOST = 'smtp.gmail.com'
    SMTP_PORT = 465
    IMAP_HOST = 'imap.gmail.com'
    IMAP_PORT = 993

    def __init__(self, email_account: Optional[str] = None, email_key: Optional[str] = None):
        self.email_account = email_account if email_account else environ['EMAIL_ACCOUNT']
        self.email_key = email_key if email_key else environ['EMAIL_ACCOUNT_KEY']

    def send(self, to_email: str, subject: str, content: str):
        """Send an email to a given address"""
        # build email
        msg = EmailMessage()
        msg['From'] = self.email_account
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.set_content(content)

        # send email
        server = SMTP_SSL(self.SMTP_HOST, self.SMTP_PORT)
        server.login(self.email_account, self.email_key)
        server.send_message(msg)
        server.quit()

    def _get_from_to_size(self,
            size_response: bytes,
            body_header_response: bytes) -> Tuple[str, str, int]:
        addresses = body_header_response.decode('utf8').splitlines()
        _, from_email = parseaddr(addresses[0])
        _, to_email = parseaddr(addresses[1])
        search_result = re.search(r'RFC822\.SIZE (\d+)', size_response.decode('ascii'))
        assert search_result is not None
        size = int(search_result.group(1))
        return from_email, to_email, size


    def _get_midi_attachment_from_msg(self, msg: Message) -> Tuple[Optional[str], Optional[bytes]]:
        for part in msg.walk():
            if part.get_content_type() == 'audio/midi' or \
                (part.get_content_type() == 'application/octet-stream' and \
                (part.get_filename() or '')[-4:].lower() == '.mid'):
                assert part.get('Content-Transfer-Encoding') in [None, 'base64']
                payload_encoded = part.get_payload()
                assert isinstance(payload_encoded, str)
                payload_decoded = base64.b64decode(payload_encoded)
                return part.get_filename(), payload_decoded
        return None, None

    def req_email_midi_attachments(self, mailbox: str) -> Iterator[RequestEmail]:
        """Check IMAP mailbox and return all emailed MIDIs"""
        imap = IMAP4_SSL(host=EmailClient.IMAP_HOST, port=EmailClient.IMAP_PORT, timeout=15*60)
        imap.login(self.email_account, self.email_key)
        imap.select(mailbox)
        while True:
            result, data = imap.search(None, 'UNSEEN')
            assert result == 'OK'
            for num in data[0].split():
                # get size of email, and to/from addresses
                result, data = imap.fetch(num, '(RFC822.SIZE BODY[HEADER.FIELDS (FROM TO)])')
                assert result == 'OK'
                assert isinstance(data, list)
                from_email, to_email, size = self._get_from_to_size(data[0][0], data[0][1])

                # skip if email too big
                if size > 1024*1024:
                    #imap.store(num, '+FLAGS', '\\Seen')
                    yield RequestEmail(
                        validation_result=RequestEmailValidationResult.TOO_BIG,
                        from_email=from_email,
                        to_email=to_email,
                        midi_name=None,
                        midi_data=None,
                    )
                    continue

                # parse email body
                result, data = imap.fetch(num, 'RFC822')
                assert result == 'OK'
                assert isinstance(data, list)
                msg = message_from_bytes(data[0][1])

                # look for MIDI attachment
                midi_name, midi_data = self._get_midi_attachment_from_msg(msg)
                if midi_name and midi_data:
                    yield RequestEmail(
                        validation_result=RequestEmailValidationResult.OK,
                        from_email=from_email,
                        to_email=to_email,
                        midi_name=midi_name,
                        midi_data=midi_data
                    )
                else:
                    yield RequestEmail(
                        validation_result=RequestEmailValidationResult.NO_MIDI,
                        from_email=from_email,
                        to_email=to_email,
                        midi_name=None,
                        midi_data=None,
                    )

            logging.info('Waiting for new emails...')
            tag = imap._new_tag().decode('ascii') # pylint: disable=protected-access
            imap.send(f'{tag} IDLE\r\n'.encode('ascii'))
            response = imap.readline()
            assert response == b'+ idling\r\n'
            try:
                response = imap.readline()
                if response:
                    logging.info('Received response: %s', response)
                else:
                    logging.info('Empty response, breaking...')
                    break
            except socket.timeout:
                logging.info('Timed out waiting for new email.')
                break
            imap.send(f'{tag} DONE\r\n'.encode('ascii'))
            logging.info('Received a new email?')
