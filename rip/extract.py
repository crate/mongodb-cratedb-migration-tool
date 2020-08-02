import bson
from pymongo.collection import Collection
from rich import print, progress

progress = progress.Progress(
    progress.TextColumn("{task.description} ", justify="left"),
    progress.BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}% ({task.completed}/{task.total})",
    "•",
    progress.TimeRemainingColumn(),
)


def extract_schema_from_collection(collection: Collection, partial: bool):
    schema = {"count": 0, "document": {}}
    if partial:
        count = 1
    else:
        count = collection.estimated_document_count()
    with progress:
        t = progress.add_task(collection.name, total=count)
        try:
            for document in collection.find():
                schema["count"] += 1
                schema["document"] = extract_schema_from_document(
                    document, schema["document"]
                )
                progress.update(t, advance=1)
                if partial:
                    break
        except KeyboardInterrupt:
            return schema
    return schema


def extract_schema_from_document(document: dict, schema: dict):
    for k, v in document.items():
        if k not in schema:
            schema[k] = {"count": 0, "types": {}}

        item_type = get_type(v)
        if item_type not in schema[k]["types"]:
            if item_type == "OBJECT":
                schema[k]["types"][item_type] = {"count": 0, "document": {}}
            elif item_type == "ARRAY":
                schema[k]["types"][item_type] = {"count": 0, "subtypes": {}}
            else:
                schema[k]["types"][item_type] = {"count": 0}

        schema[k]["count"] += 1
        schema[k]["types"][item_type]["count"] += 1
        if item_type == "OBJECT":
            schema[k]["types"][item_type]["document"] = extract_schema_from_document(
                v, schema[k]["types"][item_type]["document"]
            )
        elif item_type == "ARRAY":
            schema[k]["types"][item_type]["subtypes"] = extract_schema_from_array(
                v, schema[k]["types"][item_type]["subtypes"]
            )
    return schema


def extract_schema_from_array(array: list, schema: dict):
    for item in array:
        t = get_type(item)
        if t not in schema:
            if t == "OBJECT":
                schema[t] = {"count": 0, "document": {}}
            elif t == "ARRAY":
                schema[t] = {"count": 0, "subtypes": {}}
            else:
                schema[t] = {"count": 0}

        schema[t]["count"] += 1
        if t == "OBJECT":
            schema[t]["document"] = extract_schema_from_document(
                item, schema[t]["document"]
            )
        elif t == "ARRAY":
            schema[t]["subtypes"] = extract_schema_from_array(
                item, schema[t]["subtypes"]
            )
    return schema


TYPES_MAP = {
    # bson types
    bson.ObjectId: "OID",
    bson.datetime.datetime: "DATETIME",
    bson.Timestamp: "TIMESTAMP",
    bson.int64.Int64: "INT64",
    # primative types
    str: "STRING",
    bool: "BOOLEAN",
    int: "INTEGER",
    float: "FLOAT",
    # collection types
    list: "ARRAY",
    dict: "OBJECT",
}


def get_type(o):
    return TYPES_MAP.get(type(o), "UNKNOWN")
