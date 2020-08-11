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


def translate_object(o):
    columns = []
    object_type = "STRICT"
    for fieldname, field in o.items():
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


def translate_array(o):
    subtype, comment = determine_type(o, array=True)
    if comment:
        return f"{comment}\nARRAY({subtype})"
    else:
        return f"ARRAY({subtype})"


def determine_type(o, array=False):
    key = "subtypes" if array else "types"
    types = o.get(key, [])
    type = max(types, key=lambda item: types[item]["count"])
    if type in TYPES:
        sql_type = TYPES.get(type)
        if sql_type == "OBJECT":
            sql_type = translate_object(o[key]["OBJECT"]["document"])
        elif sql_type == "ARRAY":
            sql_type = translate_array(o[key]["ARRAY"])

        if len(types) > 1:
            return (sql_type, proportion_string(types))
        return (sql_type, None)
    return ("UNKNOWN", None)


def proportion_string(o):
    total = reduce(lambda x, y: x + o[y]["count"], list(o.keys()), 0)
    summary = "-- ⬇️ Types: "
    proportions = []
    for k in o:
        proportions.append(f"{k}: {round((o[k]['count']/total)*100, 2)}%")
    return " " + (summary + ", ".join(proportions))

def indent_sql(query):
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

def translate(o):
    tables = list(o.keys())
    for tablename in tables:
        collection = o[tablename]
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
        sql_query = BASE.format(table=tablename, columns=",\n".join(columns))
        sql_query = indent_sql(sql_query)
        syntax = Syntax(sql_query, "sql")
        rich.print(syntax)
        rich.print()
