"""Database Client Interface"""
import math
import select
from enum import Enum
from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import Optional, Iterable

import psycopg2
import psycopg2.extras

from midi_processor import MidiProcessor
from user import User, UserSerializer
from synth import Synth

class StatusEnum(Enum):
    """Enum representing queue item states"""
    NEW = 'new'
    RECORDING = 'recording'
    ENCODING = 'encoding'
    UPLOADING = 'uploading'
    NOTIFYING = 'notifying'
    FAILED = 'failed'
    DONE = 'done'

@dataclass
class QueueItem:
    """Struct for an enqueable queue item"""
    uuid: UUID
    status: StatusEnum
    retries: int
    user: User
    synth: Synth
    midi_file: str
    midi_length: int

    @staticmethod
    def factory(user: User, synth: Synth, midi_file: str, midi_data: bytes, media_path: str):
        """Create QueueItem, sync MIDI to disk, and populate default fields"""
        uuid = uuid4()
        midi_path = f'{media_path}/{uuid}.mid'
        with open(midi_path, 'wb') as fp:
            fp.write(midi_data)
        return QueueItem(
            uuid=uuid,
            status=StatusEnum.NEW,
            retries=0,
            user=user,
            synth=synth,
            midi_file=midi_file,
            midi_length=MidiProcessor.get_length(midi_path)
        )

    def midi_path(self, media_path: str):
        """Generate the filesystem path to the MIDI file"""
        return f'{media_path}/{self.uuid}.mid'

class Queue:
    """Queue interface based on postgres"""
    con: Optional[psycopg2.extensions.connection] = None

    @classmethod
    def connect(cls, connection_url):
        """Make connection to postgres"""
        cls.con = psycopg2.connect(connection_url)
        cls.con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

    @classmethod
    def disconnect(cls):
        """Disconnect from postgres"""
        if cls.con:
            cls.con.close()
            cls.con = None

    @classmethod
    def _get_cursor(cls):
        if cls.con is None:
            raise RuntimeError("No database connection")
        return cls.con.cursor()

    @classmethod
    def enqueue_queue_item(cls, queue_item: QueueItem):
        """Add item to queue"""
        assert queue_item.status == StatusEnum.NEW
        assert queue_item.retries == 0
        cur = cls._get_cursor()
        cur.execute("""
            INSERT INTO queue(
                uuid,
                status,
                retries,
                userdata,
                synth,
                midi_file,
                midi_length
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, [
            str(queue_item.uuid),
            queue_item.status.value,
            queue_item.retries,
            UserSerializer.serialize(queue_item.user),
            queue_item.synth.get_id(),
            queue_item.midi_file,
            queue_item.midi_length
        ])

    @classmethod
    def update_queue_item_status(cls, queue_item: QueueItem, status: StatusEnum):
        """Change the status of the queue item, reset retries count"""
        cur = cls._get_cursor()
        cur.execute("""
            UPDATE queue
            SET status=%s, retries=0
            WHERE uuid=%s
        """, [
            status.value,
            str(queue_item.uuid)
        ])
        queue_item.status = status

    @classmethod
    def increment_queue_item_retries(cls, queue_item: QueueItem):
        """Increment queue item retry count"""
        cur = cls._get_cursor()
        cur.execute("""
            UPDATE queue
            SET retries = retries + 1
            WHERE uuid=%s
        """, [
            str(queue_item.uuid)
        ])
        queue_item.retries += 1

    @classmethod
    def get_queue_length(cls, synth: Synth) -> int:
        """Estimate the waiting time for the queue in minutes"""
        cur = cls._get_cursor()
        cur.execute("""
            SELECT COALESCE(SUM(midi_length), 0)
            FROM queue
            WHERE synth=%s
              AND status IN ('new', 'recording')
        """, [
            synth.get_id()
        ])
        result = cur.fetchone()
        minutes = (result[0] * 1.1) / 60. # add 10% for encoding/uploading
        return math.ceil(minutes)

    @classmethod
    def fetch_queue_items(cls, synth: Synth, timeout: int = 15*60) -> Iterable[QueueItem]:
        """Queue items generator, stop on timeout"""
        cur = cls._get_cursor()
        while True:
            queue_item = cls.get_front_queue_item(synth)
            if queue_item:
                yield queue_item
            else:
                cur.execute("LISTEN queue")

                if select.select([cls.con], [], [], timeout) == ([],[],[]):
                    break
                assert cls.con is not None
                cls.con.poll()
                while cls.con.notifies:
                    _ = cls.con.notifies.pop(0)

    @classmethod
    def get_front_queue_item(cls, synth: Synth) -> Optional[QueueItem]:
        """Return the front of the queue for the given `synth`"""
        cur = cls._get_cursor()
        cur.execute("""
            SELECT
                uuid,
                status,
                retries,
                userdata,
                synth,
                midi_file,
                midi_length
            FROM queue
            WHERE synth=%s
              AND status NOT IN ('done', 'failed')
            ORDER BY created_at
        """, [
            synth.get_id()
        ])
        result = cur.fetchone()
        if result:
            return QueueItem(
                uuid=UUID(result[0]),
                status=StatusEnum(result[1]),
                retries=result[2],
                user=UserSerializer.deserialize(result[3]),
                synth=Synth.from_id(result[4]),
                midi_file=result[5],
                midi_length=result[6],
            )
        return None
