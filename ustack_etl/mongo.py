import logging


def etl_collection(mongo_db, collection_name, fn):
    documents = mongo_db[collection_name].find()
    count = mongo_db[collection_name].count_documents({})

    logging.info(
        f"Processing {count} documents in collection "
        f"'{collection_name}'")

    for document in documents:
        try:
            fn(document)
        except Exception:
            logging.exception(
                "Error processing document in collection "
                f"'{collection_name}': {document['_id']}")
