# ustack-etl #

Framework for writing ETL processes, specifically from MongoDB to SQL.

## Usage ##

ETL processes are defined by one or more `CollectionETL` sub-classes,
which are responsible for inserting records into the SQL database for
a given document in a MongoDB collection.

### Defining the ETL process for a Collection ###

The ETL process for a MongoDB collection is defined in a sub-class of
`ustack_etl.etl.CollectionETL`. The sub-class must define:

* `mongo_collection_name`, which is the name of the MongoDB collection
  to be extracted
* `sql_metadata`, which is a SQLAlchemy `MetaData` instance,
  containing all the SQL tables that will be written to by the
  sub-class
* `process_document`, which transforms the given document and loads it
  into SQL using the provided SQL connection.

#### Example: ####

```python
import sqlalchemy

from ustack_etl.etl import CollectionETL


metadata = sqlalchemy.MetaData()
my_table = sqlalchemy.Table("my_table", metadata)


class MyCollectionETL(CollectionETL):
    mongo_collection_name = "my_collection"
    sql_metadata = metadata

    def process_document(self, sql_connection, my_document):
        sql_conn.execute(my_table.insert().values(
            # ...
        )
```

### Passing State Between ETL Processes ###

Sometimes, it is necessary for the ETL process for one collection to
build up a cache of known state, in order for another collection's ETL
process to write de-normalized data to SQL (perhaps for easier or
faster querying in your analytics or BI tool).

The `CollectionETL` which produces this cached state can specify this
by adding another member variable, named `produces`, which is a tuple
of the state name, and a function (of zero arguments) which will be
used to construct an empty state variable.

Any `CollectionETL` sub-classes which need to access this state can
include a member named `consumes`, which is set to the string name of
the state, as defined by the producer.

The ETL class will ensure that the collections are ETLed in the
correct order, so that the cache will have been generated before the
consumers need to use it.

**Note** that, as of now, only one level of dependencies is
supported. If a `CollectionETL` sub-class declares that it both
`produces` and `consumes` state, an error will be raised.

#### Example: ####

```python
class MyProducer(CollectionETL):
    # Other attributes...
    produces = ("state_name", dict)

    def process_document(self, sql_conn, my_document):
        self.state_name["some_key"] = my_document["some_value"]
        # ...

class MyConsumer(CollectionETL):
    # Other attributes...
    consumes = "state_name"

    def process_document(self, sql_conn, my_document):
        cached_value = self.state_name["some_key"]
        # ...
```

### Initiating the ETL Process ###

The ETL process is initiated by constructing an instance of
`ustack_etl.etl.ETL`, adding the `CollectionETL` classes to it, and
invoking `perform_etl`.

#### Example ####

```python
from ustack_etl.etl import ETL

etl = ETL(mongo_db, sql_engine)

etl.add_collection(MyCollection)
etl.add_collection(OtherCollection)

etl.perform_etl()
```

**Note** that the `mongo_db` and `sql_engine` instances must have a
default database set on them.

### Testing CollectionETL Sub-classes ###

Some convenience methods are provided to make it easier to test
`CollectionETL` sub-classes, in the `ustack_etl.testing` module.

Your `TestCase` can inherit from `ETLTestCase`, and define an
`add_collection` method, which will be invoked in the `setUp` to add
the `CollectionETL` sub-classes needed to test.

Within the tests, invoke `self.perform_etl()` to initiate the ETL
process, and use `self.mongo_db` and `self.sql_engine` to access the
databases. The tests will connect to the databases defined in the
`MONGODB_URI` and `SQL_URI` environment variables.

#### Example ####

```python
from ustack_etl.testing import ETLTestCase


class TestMyCollection(ETLTestCase):
    def add_collections(self, etl):
        etl.add_collection(MyCollection)

    def test_something(self):
        self.mongo_db.mycollection.insert_many([
            # ...
        ])

        self.perform_etl()

        self.sql_engine.execute("select * from mytable")

        # Assert invariants...
```

#### Testing Producers and Consumers ####

There are two classes, `MockProducer` and `MockConsumer` which can be
used when testing `CollectionETL` sub-classes that produce or consume
state.

Use `MockConsumer` to test your producer by inspecting the state that
it received.

Use `MockProducer` to test your consumers by injecting the state that
they require.

## Developing ##

The unit tests assume that you are running a local SQL and MongoDB
instance, and will connect to them using the OS environment variables
MONGODB_URI and SQL_URI.

If you are running a local Kubernetes cluster using `minikube`, you
can run `./start-databases.sh` to create the appropriate databases,
then run `./pytest` to run the unit tests against the databases
running inside minikube.

If you wish to run your own instances of MongoDB and SQL, you can set
the environment variables appropriately.
