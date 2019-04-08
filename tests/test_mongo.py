from unittest import mock

from ustack_etl.testing import DatabaseTestCase

from ustack_etl import mongo


class TestMongo(DatabaseTestCase):
    def test_etl_collection_calls_function_for_each_document_in_collection(
            self):
        self.mongo_db.collectionname.insert_many([
            {
                "uid": "UID1",
                "attribute": "value1"
            },
            {
                "uid": "UID2",
                "attribute": "value2"
            }
        ])

        callback = mock.Mock()

        mongo.etl_collection(self.mongo_db, "collectionname", callback)

        self.assertCountEqual(
            [
                mock.call({
                    "_id": mock.ANY,
                    "uid": "UID1",
                    "attribute": "value1"
                }),
                mock.call({
                    "_id": mock.ANY,
                    "uid": "UID2",
                    "attribute": "value2"
                })
            ],
            callback.call_args_list)

    def test_etl_collection_continues_processing_documents_after_error(self):
        self.mongo_db.collectionname.insert_many([
            {
                "uid": "UID1",
                "attribute": "value1"
            },
            {
                "uid": "RAISESERROR",
                "attribute": "value2"
            },
            {
                "uid": "UID3",
                "attribute": "value3"
            }
        ])

        callback = mock.Mock()
        callback.side_effect = [None, Exception, None]

        mongo.etl_collection(self.mongo_db, "collectionname", callback)

        self.assertCountEqual(
            [
                mock.call({
                    "_id": mock.ANY,
                    "uid": "UID1",
                    "attribute": "value1"
                }),
                mock.call({
                    "_id": mock.ANY,
                    "uid": "RAISESERROR",
                    "attribute": "value2"
                }),
                mock.call({
                    "_id": mock.ANY,
                    "uid": "UID3",
                    "attribute": "value3"
                })
            ],
            callback.call_args_list)
