import unittest
from unittest.mock import patch, Mock

import base64
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

from email_client import EmailClient, RequestEmail, RequestEmailValidationResult
from tests.testcase import TestCase

class EmailClientTestCase(TestCase):
    HEADER_QUERY = '(RFC822.SIZE BODY[HEADER.FIELDS (FROM TO)])'
    BODY_QUERY = 'RFC822'

    def _msg_to_header_response(self, msg, index):
        length = len(msg.as_bytes())
        return 'OK', [(
            f'{index} (RFC822.SIZE {length} FLAGS (\\Seen) BODY[HEADER.FIELDS (FROM TO)] {77}'.encode('utf8'),
            f'From: {msg["From"]}\r\nTo: {msg["To"]}\r\n\r\n'.encode('utf8'),
            b')',
        )]

    def _msg_to_body_response(self, msg, index):
        as_bytes = msg.as_bytes()
        return 'OK', [(
            f'{index} (RFC822 {{{len(as_bytes)}}}'.encode('utf8'),
            as_bytes,
            b')',
        )]

    @patch('email_client.IMAP4_SSL')
    def test_req_email_midi_attachments(self, mock_imap):
        # setup email messages
        msg_nomidi = MIMEMultipart()
        msg_nomidi['From'] = 'Someone <foo@gmail.com>'
        msg_nomidi['To'] = 'bar+sc55mk2@gmail.com'
        msg_nomidi['Subject'] = 'no midi'
        attachment = MIMEText('here it is')
        msg_nomidi.attach(attachment)
        attachment = MIMEBase('image', 'jpeg')
        attachment.add_header('Content-Disposition', 'attachment', filename='me.jpg')
        attachment.set_payload(b'data')
        msg_nomidi.attach(attachment)

        msg_toobig = MIMEMultipart()
        msg_toobig['From'] = 'Someone <foo@gmail.com>'
        msg_toobig['To'] = 'bar+sc55mk2@gmail.com'
        msg_toobig['Subject'] = 'too big'
        attachment = MIMEText('here it is')
        msg_toobig.attach(attachment)
        attachment = MIMEBase('audio', 'midi')
        attachment.add_header('Content-Disposition', 'attachment', filename='mymidi.mid')
        attachment.set_payload(b'x'*1025*1024)
        msg_toobig.attach(attachment)

        msg_ok = MIMEMultipart()
        msg_ok['From'] = 'Someone <foo@gmail.com>'
        msg_ok['To'] = 'bar+sc55mk2@gmail.com'
        msg_ok['Subject'] = 'ok'
        attachment = MIMEText('here it is')
        msg_ok.attach(attachment)
        attachment = MIMEBase('audio', 'midi')
        attachment.add_header('Content-Disposition', 'attachment', filename='mymidi.mid')
        attachment['Content-Transfer-Encoding'] = 'base64'
        attachment.set_payload(base64.b64encode(b'data'))
        msg_ok.attach(attachment)


        # setup imap mock
        imap = Mock()
        imap.search.return_value = ('OK', [b'1 2 3'])
        def imap_fetch(message_set, message_parts):
            if message_set == b'1' and message_parts == self.HEADER_QUERY:
                return self._msg_to_header_response(msg_nomidi, 1)
            if message_set == b'1' and message_parts == self.BODY_QUERY:
                return self._msg_to_body_response(msg_nomidi, 1)
            if message_set == b'2' and message_parts == self.HEADER_QUERY:
                return self._msg_to_header_response(msg_toobig, 2)
            if message_set == b'2' and message_parts == self.BODY_QUERY:
                return self._msg_to_body_response(msg_toobig, 2)
            if message_set == b'3' and message_parts == self.HEADER_QUERY:
                return self._msg_to_header_response(msg_ok, 3)
            if message_set == b'3' and message_parts == self.BODY_QUERY:
                return self._msg_to_body_response(msg_ok, 3)
        imap.fetch.side_effect = imap_fetch
        imap.readline.side_effect = [b'+ idling\r\n', socket.timeout()]
        mock_imap.return_value = imap

        # setup email client
        email = EmailClient()
        result = list(email.req_email_midi_attachments('bogus_mailbox'))

        # tests
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0],
            RequestEmail(
                validation_result=RequestEmailValidationResult.NO_MIDI,
                from_email='foo@gmail.com',
                to_email='bar+sc55mk2@gmail.com',
                midi_name=None,
                midi_data=None
            )
        )
        self.assertEqual(result[1],
            RequestEmail(
                validation_result=RequestEmailValidationResult.TOO_BIG,
                from_email='foo@gmail.com',
                to_email='bar+sc55mk2@gmail.com',
                midi_name=None,
                midi_data=None
            )
        )
        self.assertEqual(result[2],
            RequestEmail(
                validation_result=RequestEmailValidationResult.OK,
                from_email='foo@gmail.com',
                to_email='bar+sc55mk2@gmail.com',
                midi_name='mymidi.mid',
                midi_data=b'data'
            )
        )

    @patch('email_client.SMTP_SSL')
    def test_send(self, mock_smtp):
        smtp = Mock()
        mock_smtp.return_value = smtp
        email = EmailClient(email_account='bar@gmail.com', email_key='my-account-key')
        email.send(
            to_email='foo@gmail.com',
            subject='my subject',
            content='my content'
        )
        self.assertEqual(smtp.login.call_args.args, ('bar@gmail.com', 'my-account-key'))
        msg = smtp.send_message.call_args.args[0]
        self.assertEqual(msg['From'], 'bar@gmail.com')
        self.assertEqual(msg['To'], 'foo@gmail.com')
        self.assertEqual(msg['Subject'], 'my subject')
        self.assertEqual(msg.get_content().strip(), 'my content')
