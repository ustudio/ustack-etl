import sqlalchemy

from ustack_etl.testing import DatabaseTestCase

from ustack_etl.etl import ETL, CollectionETL


class TestETL(DatabaseTestCase):
    def test_performs_etl_on_documents_in_collections(self):
        meta = sqlalchemy.MetaData()
        sample_table = sqlalchemy.Table(
            "sample", meta,
            sqlalchemy.Column("uid", sqlalchemy.Text, primary_key=True))

        self.mongo_db.samplecollection.insert_many([
            {
                "uid": "DOCUMENT1"
            },
            {
                "uid": "DOCUMENT2"
            }
        ])

        class SampleCollectionETL(CollectionETL):
            mongo_collection_name = "samplecollection"
            sql_metadata = meta

            def process_document(self, sql_conn, document):
                sql_conn.execute(
                    sample_table.insert().values(
                        uid=document["uid"]))

        etl = ETL(self.mongo_db, self.sql_engine)

        etl.add_collection(SampleCollectionETL)

        etl.perform_etl()

        sql_cursor = self.sql_engine.execute("select * from sample")

        self.assertCountEqual(
            [
                {
                    "uid": "DOCUMENT1"
                },
                {
                    "uid": "DOCUMENT2"
                }
            ],
            [dict(row) for row in sql_cursor.fetchall()])

    def test_perform_etl_passes_state_between_dependent_collectiosn(self):
        first_meta = sqlalchemy.MetaData()
        first_table = sqlalchemy.Table(
            "first", first_meta,
            sqlalchemy.Column("uid", sqlalchemy.Text, primary_key=True),
            sqlalchemy.Column("attribute", sqlalchemy.Text))

        second_meta = sqlalchemy.MetaData()
        second_table = sqlalchemy.Table(
            "second", second_meta,
            sqlalchemy.Column("uid", sqlalchemy.Text, primary_key=True),
            sqlalchemy.Column("attribute", sqlalchemy.Text))

        self.mongo_db.firstcollection.insert_many([
            {
                "uid": "DOCUMENT1",
                "attribute": "ATTR1"
            },
            {
                "uid": "DOCUMENT2",
                "attribute": "ATTR2"
            }
        ])

        self.mongo_db.secondcollection.insert_many([
            {
                "uid": "SECOND1",
                "first": "DOCUMENT1"
            },
            {
                "uid": "SECOND2",
                "first": "DOCUMENT2"
            }
        ])

        class FirstCollectionETL(CollectionETL):
            mongo_collection_name = "firstcollection"
            sql_metadata = first_meta
            produces = ("first_attribute_mapping", dict)

            def process_document(self, sql_conn, document):
                self.first_attribute_mapping[document["uid"]] = \
                    document["attribute"]

                sql_conn.execute(
                    first_table.insert().values(
                        uid=document["uid"],
                        attribute=document["attribute"]))

        class SecondCollectionETL(CollectionETL):
            mongo_collection_name = "secondcollection"
            sql_metadata = second_meta
            consumes = "first_attribute_mapping"

            def process_document(self, sql_conn, document):
                sql_conn.execute(
                    second_table.insert().values(
                        uid=document["uid"],
                        attribute=self.first_attribute_mapping[
                            document["first"]]))

        etl = ETL(self.mongo_db, self.sql_engine)

        etl.add_collection(SecondCollectionETL)
        etl.add_collection(FirstCollectionETL)

        etl.perform_etl()

        sql_cursor = self.sql_engine.execute("select * from first")

        self.assertCountEqual(
            [
                {
                    "uid": "DOCUMENT1",
                    "attribute": "ATTR1"
                },
                {
                    "uid": "DOCUMENT2",
                    "attribute": "ATTR2"
                }
            ],
            [dict(row) for row in sql_cursor.fetchall()])

        sql_cursor = self.sql_engine.execute("select * from second")

        self.assertCountEqual(
            [
                {
                    "uid": "SECOND1",
                    "attribute": "ATTR1"
                },
                {
                    "uid": "SECOND2",
                    "attribute": "ATTR2"
                }
            ],
            [dict(row) for row in sql_cursor.fetchall()])

    def test_add_collection_raises_exception_on_chained_dependencies(self):
        meta = sqlalchemy.MetaData()

        class ChainedDependency(CollectionETL):
            mongo_collection_name = "chaineddependency"
            sql_metadata = meta
            consumes = "input"
            produces = ("output", dict)

            def process_document(self, sql_conn, document):
                pass

        etl = ETL(self.mongo_db, self.sql_engine)

        with self.assertRaises(ValueError):
            etl.add_collection(ChainedDependency)

    def test_perform_etl_skips_documents_that_generate_errors(self):
        meta = sqlalchemy.MetaData()
        sample_table = sqlalchemy.Table(
            "sample", meta,
            sqlalchemy.Column("uid", sqlalchemy.Text, primary_key=True))

        self.mongo_db.samplecollection.insert_many([
            {
                "uid": "DOCUMENT1"
            },
            {
                "document": "generates error"
            },
            {
                "uid": "DOCUMENT3"
            }
        ])

        class SampleCollectionETL(CollectionETL):
            mongo_collection_name = "samplecollection"
            sql_metadata = meta

            def process_document(self, sql_conn, document):
                sql_conn.execute(
                    sample_table.insert().values(
                        uid=document["uid"]))

        etl = ETL(self.mongo_db, self.sql_engine)

        etl.add_collection(SampleCollectionETL)

        etl.perform_etl()

        sql_cursor = self.sql_engine.execute("select * from sample")

        self.assertCountEqual(
            [
                {
                    "uid": "DOCUMENT1"
                },
                {
                    "uid": "DOCUMENT3"
                }
            ],
            [dict(row) for row in sql_cursor.fetchall()])
