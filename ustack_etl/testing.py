import datetime
from datetime import timezone
import os
import unittest
import urllib

from bson.objectid import ObjectId
import pymongo
import sqlalchemy
import sqlalchemy_utils

from ustack_etl.etl import ETL, CollectionETL


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self.mongo_client = pymongo.MongoClient(os.environ["MONGODB_URI"])
        self.mongo_db = self.mongo_client.get_database()
        self.addCleanup(lambda: self.mongo_client.drop_database(self.mongo_db))

        sql_uri = os.environ["SQL_URI"]
        parsed_sql_uri = urllib.parse.urlparse(sql_uri)

        netloc = f"testreader@{parsed_sql_uri.hostname}"
        if parsed_sql_uri.port is not None:
            netloc += f":{parsed_sql_uri.port}"

        reader_sql_uri = urllib.parse.urlunparse((
            parsed_sql_uri.scheme, netloc, parsed_sql_uri.path,
            parsed_sql_uri.params,
            parsed_sql_uri.query, parsed_sql_uri.fragment))

        sqlalchemy_utils.create_database(sql_uri)
        self.sql_engine = sqlalchemy.create_engine(sql_uri)
        self.addCleanup(lambda: sqlalchemy_utils.drop_database(sql_uri))

        with self.sql_engine.begin() as sql_conn:
            sql_conn.execute("create role testreader login")
            sql_conn.execute("create role readers")
            sql_conn.execute("grant readers to testreader")

        self.addCleanup(self._cleanup_testreader)

        self.reader_sql_engine = sqlalchemy.create_engine(reader_sql_uri)
        self.addCleanup(self.reader_sql_engine.dispose)

    def _cleanup_testreader(self):
        with self.sql_engine.begin() as sql_conn:
            sql_conn.execute("drop owned by testreader")
            sql_conn.execute("drop role testreader")
            sql_conn.execute("drop owned by readers")
            sql_conn.execute("drop role readers")

    def object_id_from_datetime(self, *args):
        return ObjectId.from_datetime(
            datetime.datetime(*args, tzinfo=timezone.utc))


class MockConsumer():
    def __init__(self, mapping_name):
        self.mapping_name = mapping_name

        self.consumes = self.mapping_name
        self.mongo_collection_name = "mock_consumer"

    def __call__(self):
        class _MockConsumerInstance(CollectionETL):
            sql_metadata = sqlalchemy.MetaData()
            mongo_collection_name = self.mongo_collection_name

            def __setattr__(inst, name, value):
                if name == self.mapping_name:
                    self.captured_state = value

                super().__setattr__(name, value)

            def process_document(inst, sql_conn, document):
                pass

        return _MockConsumerInstance()


class MockProducer():
    def __init__(self, mapping_name, mapping_value):
        self.mapping_name = mapping_name

        self.consumes = "__none__"
        self.produces = (self.mapping_name, lambda: mapping_value)
        self.mongo_collection_name = "mock_producer"

    def __call__(self):
        class _MockProducerInstance(CollectionETL):
            sql_metadata = sqlalchemy.MetaData()
            mongo_collection_name = self.mongo_collection_name

            def process_document(inst, sql_conn, document):
                pass

        return _MockProducerInstance()


class ETLTestCase(DatabaseTestCase):
    def perform_etl(self):
        etl = ETL(self.mongo_db, self.sql_engine)

        self.add_collections(etl)

        etl.perform_etl()

    def add_collections(self, etl):
        pass
