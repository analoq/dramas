"""create queue table

Revision ID: 3e112e2b2014
Revises: 
Create Date: 2023-12-09 22:48:49.982866

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3e112e2b2014'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
        CREATE TYPE synth_enum AS ENUM(
            'sc55mk2'
        )
    """)
    op.execute("""
        CREATE TYPE status_enum AS ENUM(
            'new',
            'recording',
            'encoding',
            'uploading',
            'notifying',
            'done',
            'failed'
        )
    """)
    op.execute("""
        CREATE TABLE queue(
            uuid            UUID PRIMARY KEY,
            status          status_enum NOT NULL DEFAULT 'new',
            priority        INT NOT NULL DEFAULT '0',
            retries         INT NOT NULL DEFAULT '0',
            userdata        JSONB NOT NULL,
            synth           synth_enum NOT NULL,
            midi_file       VARCHAR(80) NOT NULL,
            midi_length     INT NOT NULL,
            created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE FUNCTION queue_notify() RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify('queue', NULL);
            RETURN NULL;
        END
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER queue_notify_trigger
        AFTER INSERT ON queue
        FOR EACH ROW EXECUTE FUNCTION queue_notify()
    """)

def downgrade() -> None:
    op.execute("""DROP TRIGGER queue_notify_trigger ON queue""")
    op.execute("""DROP FUNCTION queue_notify""")
    op.drop_table('queue')
    op.execute("""DROP TYPE status_enum""")
    op.execute("""DROP TYPE synth_enum""")
