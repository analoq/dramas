import unittest

from dotenv import load_dotenv


class TestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        load_dotenv('.env.test')
