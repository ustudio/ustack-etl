import sqlalchemy

from ustack_etl.testing import DatabaseTestCase

from ustack_etl import sql


class TestSQL(DatabaseTestCase):
    def test_create_table_creates_table_and_grants_read_permissions(self):
        meta = sqlalchemy.MetaData()
        table = sqlalchemy.Table(
            "table_name", meta,
            sqlalchemy.Column("id", sqlalchemy.Text, primary_key=True))

        sql.create_table(self.sql_engine, table)

        with self.sql_engine.begin() as sql_conn:
            sql_conn.execute(table.insert().values(id="SOME-ID"))

        sql_cursor = self.reader_sql_engine.execute("select * from table_name")

        self.assertEqual(
            [
                {"id": "SOME-ID"}
            ],
            [dict(row) for row in sql_cursor.fetchall()])

    def test_create_table_empties_table_when_it_already_exists(self):
        meta = sqlalchemy.MetaData()
        table = sqlalchemy.Table(
            "table_name", meta,
            sqlalchemy.Column("id", sqlalchemy.Text, primary_key=True))
        sql.create_table(self.sql_engine, table)
        with self.sql_engine.begin() as sql_conn:
            sql_conn.execute(table.insert().values(id="REMOVED-DATA"))

        sql.create_table(self.sql_engine, table)

        with self.sql_engine.begin() as sql_conn:
            sql_conn.execute(table.insert().values(id="SOME-ID"))

        sql_cursor = self.reader_sql_engine.execute("select * from table_name")

        self.assertEqual(
            [
                {"id": "SOME-ID"}
            ],
            [dict(row) for row in sql_cursor.fetchall()])

    def test_sanitize_text_returns_text_with_null_characters_removed(self):
        result = sql.sanitize_text("text\x00with\x00null\x00characters")

        self.assertEqual("textwithnullcharacters", result)
