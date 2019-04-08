import logging


def etl_collection(mongo_db, collection_name, fn):
    documents = mongo_db[collection_name].find()

    logging.info(
        f"Processing {documents.count()} documents in collection "
        f"'{collection_name}'")

    for document in documents:
        try:
            fn(document)
        except Exception:
            logging.exception(
                "Error processing document in collection "
                f"'{collection_name}': {document['_id']}")
