from unittest import mock

import pymongo

from crate.migr8.__main__ import parse_input_numbers, gather_collections

import unittest


class TestInputNumberParser(unittest.TestCase):
    def test_numbers(self):
        s = "0 1 7 4"
        parsed = parse_input_numbers(s)
        self.assertEqual(parsed, [0, 1, 7, 4])

    def test_comma_seperated_numbers(self):
        s = "0, 1, 7, 4"
        parsed = parse_input_numbers(s)
        self.assertEqual(parsed, [0, 1, 7, 4])

    def test_mixed_numbers(self):
        s = "0 1, 7 4"
        parsed = parse_input_numbers(s)
        self.assertEqual(parsed, [0, 1, 7, 4])

    def test_range(self):
        s = "1-5"
        parsed = parse_input_numbers(s)
        self.assertEqual(parsed, [1, 2, 3, 4, 5])

    def test_inverse_range(self):
        s = "5-1"
        parsed = parse_input_numbers(s)
        self.assertEqual(parsed, [1, 2, 3, 4, 5])

    def test_mixed(self):
        s = "0 1, 3 5-8, 9 12-10"
        parsed = parse_input_numbers(s)
        self.assertEqual(parsed, [0, 1, 3, 5, 6, 7, 8, 9, 10, 11, 12])


class TestMongoDBIntegration(unittest.TestCase):
    """
    A few conditional integration test cases with MongoDB.

    It can be configured to not fail the test suite when no MongoDB server
    is running. In order to provide an instance easily, use Docker or Podman.

    # MongoDB 4
    docker run -it --rm --publish=27017:27017 mongo:4

    # MongoDB 5
    docker run -it --rm --publish=27017:27017 mongo:5
    """

    HOST = "localhost"
    PORT = 27017
    DBNAME = "testdrive"
    TIMEOUT_MS = 200

    SKIP_IF_NOT_RUNNING = False

    @classmethod
    def setUpClass(cls):
        cls.client = pymongo.MongoClient(
            host=cls.HOST,
            port=cls.PORT,
            connectTimeoutMS=cls.TIMEOUT_MS,
            serverSelectionTimeoutMS=cls.TIMEOUT_MS,
        )
        cls.db = cls.client.get_database(cls.DBNAME)
        try:
            cls.db.last_status()
        except pymongo.errors.ServerSelectionTimeoutError:
            if cls.SKIP_IF_NOT_RUNNING:
                raise cls.skipTest(cls, reason="MongoDB server not running")
            else:
                raise

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.DBNAME)
        cls.client.close()

    def test_gather_collections(self):
        """
        Verify if core method `gather_collections` works as expected.
        """
        self.db.create_collection("foobar")
        with mock.patch("builtins.input", return_value="unknown"):
            collections = gather_collections(database=self.db)
            self.assertEqual(collections, ["foobar"])
