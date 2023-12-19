from os import environ, path, unlink
from dataclasses import asdict
from uuid import UUID, uuid4
import io

import mido

from tests.db_testcase import DBTestCase

from queue_client import Queue, QueueItem, StatusEnum
from synth import SynthRolandSC55mk2
from user import UserEmail, UserDiscord

class QueueTestCase(DBTestCase):
    def test_queuing(self):
        Queue.connect(environ['DATABASE_URL'])

        front_item = Queue.get_front_queue_item(SynthRolandSC55mk2())
        self.assertIsNone(front_item, "get_front_queue_item returned something for an empty queue")

        queue_item_1 = QueueItem(
            uuid=uuid4(),
            status=StatusEnum.NEW,
            retries=0,
            user=UserDiscord(user_id=1, channel_id=2),
            synth=SynthRolandSC55mk2(),
            midi_file='canyon.mid',
            midi_length=300,
        )
        Queue.enqueue_queue_item(queue_item_1)

        queue_item_2 = QueueItem(
            uuid=uuid4(),
            status=StatusEnum.NEW,
            retries=0,
            user=UserEmail(email='foo@bar.com'),
            synth=SynthRolandSC55mk2(),
            midi_file='onestop.mid',
            midi_length=500,
        )
        Queue.enqueue_queue_item(queue_item_2)

        #self.assertTrue(Queue.wait_for_queue_item(), "wait_for_queue_item() should return true") 
        
        front_item = Queue.get_front_queue_item(SynthRolandSC55mk2())
        self.assertEqual(front_item, queue_item_1, "get_front_queue_item returned wrong item")

        Queue.update_queue_item_status(queue_item_1, StatusEnum.DONE)
        self.assertEqual(queue_item_1.status, StatusEnum.DONE)
        front_item = Queue.get_front_queue_item(SynthRolandSC55mk2())
        self.assertEqual(front_item, queue_item_2, "get_front_queue_item returned wrong item")

        Queue.disconnect()

    def test_increment_queue_item_retries(self):
        Queue.connect(environ['DATABASE_URL'])
        queue_item = QueueItem(
            uuid=uuid4(),
            status=StatusEnum.NEW,
            retries=0,
            user=UserEmail(email='foo@bar.com'),
            synth=SynthRolandSC55mk2(),
            midi_file='onestop.mid',
            midi_length=500
        )
        Queue.enqueue_queue_item(queue_item)
        Queue.increment_queue_item_retries(queue_item)
        self.assertEqual(queue_item.retries, 1)
        Queue.disconnect()

    def test_get_queue_length(self):
        Queue.connect(environ['DATABASE_URL'])
        queue_item_1 = QueueItem(
            uuid=uuid4(),
            status=StatusEnum.NEW,
            retries=0,
            user=UserEmail(email='foo@bar.com'),
            synth=SynthRolandSC55mk2(),
            midi_file='onestop.mid',
            midi_length=60
        )
        Queue.enqueue_queue_item(queue_item_1)
        queue_item_2 = QueueItem(
            uuid=uuid4(),
            status=StatusEnum.NEW,
            retries=0,
            user=UserEmail(email='foo@bar.com'),
            synth=SynthRolandSC55mk2(),
            midi_file='canyon.mid',
            midi_length=120
        )
        Queue.enqueue_queue_item(queue_item_2)
        self.assertTrue(Queue.get_queue_length(SynthRolandSC55mk2()) >= 3)
        Queue.disconnect()

    def test_fetch_queue_items(self):
        Queue.connect(environ['DATABASE_URL'])
        queue_item_1 = QueueItem(
            uuid=uuid4(),
            status=StatusEnum.NEW,
            retries=0,
            user=UserEmail(email='foo@bar.com'),
            synth=SynthRolandSC55mk2(),
            midi_file='onestop.mid',
            midi_length=60
        )
        Queue.enqueue_queue_item(queue_item_1)
        queue_item_2 = QueueItem(
            uuid=uuid4(),
            status=StatusEnum.NEW,
            retries=0,
            user=UserEmail(email='foo@bar.com'),
            synth=SynthRolandSC55mk2(),
            midi_file='canyon.mid',
            midi_length=120
        )
        Queue.enqueue_queue_item(queue_item_2)

        queue_items = []
        for queue_item in Queue.fetch_queue_items(SynthRolandSC55mk2(), timeout=1):
            queue_items.append(queue_item)
            Queue.update_queue_item_status(queue_item, StatusEnum.DONE)
        self.assertEquals(queue_items[0].uuid, queue_item_1.uuid)
        self.assertEquals(queue_items[1].uuid, queue_item_2.uuid)

        Queue.disconnect()

    def test_queue_item_factory(self):
        stream = io.BytesIO()
        midi = mido.MidiFile(ticks_per_beat=24)
        track = mido.MidiTrack()
        track.append(mido.Message('note_on', note=64, velocity=64, time=0))
        track.append(mido.Message('note_off', note=64, velocity=64, time=24*2*60))
        midi.tracks.append(track)
        midi.save(file=stream)

        queue_item = QueueItem.factory(
            user=UserEmail(email='foo@bar.com'),
            synth=SynthRolandSC55mk2(),
            midi_file='town.mid',
            midi_data=stream.getvalue(),
            media_path='/tmp'
        )
        self.assertEquals(queue_item.status, StatusEnum.NEW)
        self.assertEquals(queue_item.midi_length, 60)
        self.assertTrue(path.exists(queue_item.midi_path('/tmp')))
        unlink(queue_item.midi_path('/tmp'))
