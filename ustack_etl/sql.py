def create_table(sql_engine, table):
    with sql_engine.begin() as sql_conn:
        table.drop(sql_conn, checkfirst=True)
        table.create(sql_conn)
        sql_conn.execute(f"grant select on \"{table.name}\" to readers")


def sanitize_text(text):
    return text.replace("\x00", "")
