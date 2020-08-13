""" Translates a MongoDB collection schema into a CrateDB CREATE TABLE expression.

Given a generated MongoDB collection schema, this will translate that schema
into a CREATE TABLE statement, mapping fields to columns and the collection
name to the table name.

In the case where there are type conflicts (for example, 40% of the values
for a field are integers, and 60% are strings), the translator will choose
the type with the greatest proportion.
"""

import rich
from functools import reduce
from rich.syntax import Syntax

TYPES = {
    "DATETIME": "TIMESTAMP WITH TIME ZONE",
    "INT64": "INTEGER",
    "STRING": "TEXT",
    "BOOLEAN": "BOOLEAN",
    "INTEGER": "INTEGER",
    "FLOAT": "FLOAT",
    "ARRAY": "ARRAY",
    "OBJECT": "OBJECT",
}

BASE = """
CREATE TABLE IF NOT EXISTS "doc"."{table}" (\n{columns}\n);
"""

COLUMN = '"{column_name}" {type}'

OBJECT = "OBJECT ({object_type}) AS (\n{definition}\n)"


def translate_object(schema):
    """ Translates an object field schema definition into a CrateDB dynamic
    object column.
    """

    columns = []
    object_type = "DYNAMIC"
    for fieldname, field in schema.items():
        sql_type, comment = determine_type(field)
        columns.append((COLUMN.format(column_name=fieldname, type=sql_type), comment))
    for index, column in enumerate(columns):
        if column[1]:
            columns[index] = f"{column[1]}\n{column[0]}"
        else:
            columns[index] = column[0]
    return OBJECT.format(
        object_type=object_type, definition=",\n".join([c for c in columns]),
    )


def translate_array(schema):
    """ Translates an array field schema definition into a CrateDB array column.
    """

    subtype, comment = determine_type(schema)
    if comment:
        return f"{comment}\nARRAY({subtype})"
    else:
        return f"ARRAY({subtype})"


def determine_type(schema):
    """ Determine the type of a specific field schema.
    """

    types = schema.get("types", [])
    type = max(types, key=lambda item: types[item]["count"])
    if type in TYPES:
        sql_type = TYPES.get(type)
        if sql_type == "OBJECT":
            sql_type = translate_object(types["OBJECT"]["document"])
        elif sql_type == "ARRAY":
            sql_type = translate_array(types["ARRAY"])

        if len(types) > 1:
            return (sql_type, proportion_string(types))
        return (sql_type, None)
    return ("UNKNOWN", None)


def proportion_string(types: list) -> str:
    """ Converts a list of types into a string explaining the proportions of
    each type.
    """

    total = reduce(lambda x, y: x + types[y]["count"], list(types.keys()), 0)
    summary = "-- ⬇️ Types: "
    proportions = []
    for type in types:
        proportions.append(f"{type}: {round((types[type]['count']/total)*100, 2)}%")
    return " " + (summary + ", ".join(proportions))


def indent_sql(query: str) -> str:
    """ Indents an SQL query based on opening and closing brackets.
    """

    indent = 0
    lines = query.split("\n")
    for idx, line in enumerate(lines):
        lines[idx] = (" " * indent) + line
        if len(line) >= 1:
            if line[-1] == "(":
                indent += 4
            elif line[-1] == ")":
                indent -= 4
    return "\n".join(lines)


def translate(schemas):
    """ Translate a schema definition for a set of MongoDB collection schemas.

    This results in a set of CrateDB compatible CREATE TABLE expressions
    corresponding to the set of MongoDB collection schemas.
    """

    tables = list(schemas.keys())
    sql_queries = {}
    for tablename in tables:
        collection = schemas[tablename]
        columns = []
        for fieldname, field in collection["document"].items():
            sql_type, comment = determine_type(field)
            if sql_type != "UNKNOWN":
                columns.append(
                    (COLUMN.format(column_name=fieldname, type=sql_type), comment)
                )

        for index, column in enumerate(columns):
            if column[1]:
                columns[index] = f"{column[1]}\n{column[0]}"
            else:
                columns[index] = column[0]
        sql_queries[tablename] = indent_sql(
            BASE.format(table=tablename, columns=",\n".join(columns))
        )
    return sql_queries
