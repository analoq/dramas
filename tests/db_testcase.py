from alembic import command, config

from tests.testcase import TestCase

class DBTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.cfg = config.Config('alembic.ini')
        command.upgrade(self.cfg, "head")

    def tearDown(self):
        super().tearDown()
        command.downgrade(self.cfg, "base")

