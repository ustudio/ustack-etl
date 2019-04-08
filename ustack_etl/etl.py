from collections import defaultdict
import logging

from ustack_etl import mongo
from ustack_etl import sql


class _StateDependency():
    def __init__(self, mongo_db, sql_engine):
        self.consumers = []
        self.producer = None
        self.mongo_db = mongo_db
        self.sql_engine = sql_engine

    def set_producer(self, state_constructor, producer):
        self.state_constructor = state_constructor
        self.producer = producer

    def add_consumer(self, consumer):
        self.consumers.append(consumer)

    def _perform_single_etl(self, attribute_name, state, collection_etl_class):
        logging.info(
            "Starting ETL process for collection "
            f"''{collection_etl_class.mongo_collection_name}'")

        collection_etl = collection_etl_class()

        setattr(collection_etl, attribute_name, state)

        for table in collection_etl.sql_metadata.tables.values():
            sql.create_table(self.sql_engine, table)

        def process_document(document):
            with self.sql_engine.begin() as sql_conn:
                collection_etl.process_document(sql_conn, document)

        mongo.etl_collection(
            self.mongo_db, collection_etl.mongo_collection_name,
            process_document)

        logging.info(
            "Completed ETL process for collection "
            f"'{collection_etl_class.mongo_collection_name}'")

    def perform_etl(self, attribute_name):
        state = None

        if self.producer is not None:
            state = self.state_constructor()

            self._perform_single_etl(attribute_name, state, self.producer)

        for consumer in self.consumers:
            self._perform_single_etl(attribute_name, state, consumer)


class ETL():
    def __init__(self, mongo_db, sql_engine):
        self.mongo_db = mongo_db
        self.sql_engine = sql_engine
        self.collection_dependencies = defaultdict(
            lambda: _StateDependency(self.mongo_db, self.sql_engine))

    def add_collection(self, collection_etl_class):
        if hasattr(collection_etl_class, "produces"):
            produces_attribute, state_constructor = \
                collection_etl_class.produces

            if collection_etl_class.consumes != "__none__":
                raise ValueError(
                    f"Invalid CollectionETL: {collection_etl_class} cannot "
                    f"produce {produces_attribute} as a consumer of "
                    f"{collection_etl_class.consumes}")

            self.collection_dependencies[produces_attribute].set_producer(
                state_constructor, collection_etl_class)
        else:
            self.collection_dependencies[
                collection_etl_class.consumes].add_consumer(
                    collection_etl_class)

    def perform_etl(self):
        for attribute_name, dependency in self.collection_dependencies.items():
            dependency.perform_etl(attribute_name)


class CollectionETL():
    consumes = "__none__"
