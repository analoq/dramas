"""Script to ingest emailed MIDI attachments and enqeue them"""
from os import environ
import logging
import re

from dotenv import load_dotenv
import sdnotify # type: ignore

from email_client import EmailClient, RequestEmailValidationResult
from queue_client import Queue, QueueItem
from synth import Synth
from user import UserEmail
from midi_validator import MidiValidator, MidiValidatorResult

load_dotenv()

def get_synth_id(to_email: str) -> str:
    """Extract the synth id from the email's TO field"""
    result = re.search(r'\+(\w+)@', to_email)
    assert result is not None
    return result.group(1)

def main():
    """Main program"""
    logging.basicConfig(level=logging.INFO)
    logging.info('Started.')
    system_notifier = sdnotify.SystemdNotifier()
    email = EmailClient(
        email_account=environ['EMAIL_ACCOUNT'],
        email_key=environ['EMAIL_ACCOUNT_KEY']
    )
    system_notifier.notify('READY=1')
    while True:
        logging.info('Fetching request emails...')
        for request_email in email.req_email_midi_attachments(mailbox='dtmaas'):
            logging.info('Received request email from %s to %s',
                request_email.from_email, request_email.to_email)
            logging.info('Watchdog pulse...')
            system_notifier.notify("WATCHDOG=1")
            if request_email.validation_result == RequestEmailValidationResult.OK:
                logging.info('Request email validated, validating MIDI...')
                midi_validation_result = MidiValidator.get_result(request_email.midi_data)
                if midi_validation_result == MidiValidatorResult.OK:
                    logging.info('MIDI file "%s" valid, enqueueing...', request_email.midi_name)

                    synth_id = get_synth_id(request_email.to_email)
                    synth = Synth.from_id(synth_id)
                    queue_item = QueueItem.factory(
                        user=UserEmail(email=request_email.from_email),
                        synth=synth,
                        midi_file=request_email.midi_name,
                        midi_data=request_email.midi_data,
                        media_path=environ['MEDIA_PATH'],
                    )
                    Queue.connect(environ['DATABASE_URL'])
                    Queue.enqueue_queue_item(queue_item)
                    minutes = Queue.get_queue_length(synth)
                    Queue.disconnect()

                    logging.info('Enqueued with id "%s", sending notification...', queue_item.uuid)
                    content = f'Your MIDI file "{queue_item.midi_file}" looks good ' \
                        f'and is slated to be recorded on a {synth.get_name()}! ' \
                        f'Expect an email in about {minutes} minutes...'
                    email.send(
                        to_email=request_email.from_email,
                        subject='DTMaaS Success Confirmation',
                        content=content
                    )
                else:
                    logging.info('MIDI status "%s", sending notification...',
                        midi_validation_result)
                    content = f'Sorry but I could not process your MIDI ' \
                        f'because "{midi_validation_result.value}"'
                    email.send(
                        to_email=request_email.from_email,
                        subject='DTMaaS Error Confirmation',
                        content=content
                    )
                    logging.info('Successfully handled email from %s', request_email.from_email)
            else:
                logging.info('Request email status "%s", sending notification...',
                    request_email.validation_result)
                content = f'Sorry but I could not process your request ' \
                    f'because "{request_email.validation_result.value}"'
                email.send(
                    to_email=request_email.from_email,
                    subject='DTMaaS Error Confirmation',
                    content=content
                )
        logging.info('Watchdog pulse...')
        system_notifier.notify("WATCHDOG=1")
    logging.error('Done?')

if __name__ == "__main__":
    main()
