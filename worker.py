"""Script that does the main work of processing MIDIs"""
import logging
import atexit
from os import environ, unlink
from os.path import basename
import sys

from dotenv import load_dotenv
import sdnotify # type: ignore

from queue_client import Queue, QueueItem, StatusEnum
from synth import Synth
from midi_processor import MidiProcessor
from azure_client import AzureClient

load_dotenv()

MAX_RETRIES = 3

def exit_handler(queue_item: QueueItem):
    """Increment retry count on unexpected exit"""
    logging.warning('Unexpected exit, incrementing retries...')
    Queue.increment_queue_item_retries(queue_item)

def process_queue_item(queue_item: QueueItem):
    """Process the queue item or mark as failed after too many retries"""
    if queue_item.retries >= MAX_RETRIES:
        logging.error('Maximum retries exceeded, marking as failed...')
        Queue.update_queue_item_status(queue_item, StatusEnum.FAILED)
        return
    atexit.register(exit_handler, queue_item=queue_item)
    assert queue_item.status not in (StatusEnum.DONE, StatusEnum.FAILED)
    midi_path = queue_item.midi_path(environ['MEDIA_PATH'])
    wav_path = f'{midi_path[:-4]}.wav'
    flac_path = f'{wav_path[:-4]}.flac'

    if queue_item.status == StatusEnum.NEW:
        Queue.update_queue_item_status(queue_item, StatusEnum.RECORDING)

    if queue_item.status == StatusEnum.RECORDING:
        logging.info('Recording MIDI file "%s"...', midi_path)
        MidiProcessor.record(queue_item.synth, midi_path, wav_path)
        Queue.update_queue_item_status(queue_item, StatusEnum.ENCODING)

    if queue_item.status == StatusEnum.ENCODING:
        logging.info('Encoding WAV file "%s"...', wav_path)
        MidiProcessor.encode(wav_path, flac_path)
        Queue.update_queue_item_status(queue_item, StatusEnum.UPLOADING)

    if queue_item.status == StatusEnum.UPLOADING:
        logging.info('Uploading FLAC file "%s"...', flac_path)
        azure = AzureClient(
            tenant_id=environ['AZURE_TENANT_ID'],
            client_id=environ['AZURE_CLIENT_ID'],
            client_secret=environ['AZURE_CLIENT_SECRET'],
            resource='https://storage.azure.com/'
        )
        with open(flac_path, 'rb') as fp:
            url = azure.req_blob_upload(
                blob_account='dtmaas',
                container='recordings',
                blob=basename(flac_path),
                data=fp
            )
        Queue.update_queue_item_status(queue_item, StatusEnum.NOTIFYING)

    if queue_item.status == StatusEnum.NOTIFYING:
        logging.info('Sending notification...')
        content = f'Your MIDI file "{queue_item.midi_file}" was recorded on a ' \
            f'{queue_item.synth.get_name()} and uploaded here:' \
            f'\r\n{url}\r\nThis link will expire after 24 hours.'
        queue_item.user.notify(content)
        Queue.update_queue_item_status(queue_item, StatusEnum.DONE)
    logging.info('Completed! Cleaning up...')
    atexit.unregister(exit_handler)
    # NOTE: these steps can fail without retry
    unlink(midi_path)
    unlink(wav_path)
    unlink(flac_path)

def main():
    """Main program"""
    logging.basicConfig(level=logging.INFO)
    logging.info('Started.')
    system_notifier = sdnotify.SystemdNotifier()

    logging.info('Connecting to queue...')
    Queue.connect(environ['DATABASE_URL'])

    synth = Synth.from_id(sys.argv[1])

    system_notifier.notify('READY=1')
    while True:
        logging.info('Fetching queue items...')
        for queue_item in Queue.fetch_queue_items(synth):
            logging.info('Received queue item: %s', queue_item)
            logging.info('Watchdog pulse...')
            system_notifier.notify('WATCHDOG=1')
            process_queue_item(queue_item)
        logging.info('Watchdog pulse...')
        system_notifier.notify('WATCHDOG=1')
    logging.info('Done.')

if __name__ == "__main__":
    main()
