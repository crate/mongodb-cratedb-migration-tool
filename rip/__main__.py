import argparse
import json

import pymongo
import rich
from rich.columns import Columns


import re

from .extract import extract_schema_from_collection
from .translate import translate as tran


def extract_parser(subargs):
    parser = subargs.add_parser(
        "extract", help="Extract a schema from a MongoDB database"
    )
    parser.add_argument("--host", default="localhost", help="MongoDB host")
    parser.add_argument("--port", default=27017, help="MongoDB port")
    parser.add_argument("--database", required=True, help="MongoDB database")
    parser.add_argument("-o", "--out", default="mongodb_schema.json")


def translate_parser(subargs):
    parser = subargs.add_parser("translate")
    parser.add_argument("-i", "--infile")


def full_parser(subargs):
    parser = subargs.add_parser(
        "full", help="Extract and translate a schema from MongoDB to CrateDB"
    )
    parser.add_argument("--host", default="localhost", help="MongoDB host")
    parser.add_argument("--port", default=27017, help="MongoDB port")
    parser.add_argument("--database", required=True, help="MongoDB database")


def get_args():
    parser = argparse.ArgumentParser(add_help=False)
    subparsers = parser.add_subparsers(dest="command")
    extract_parser(subparsers)
    translate_parser(subparsers)
    full_parser(subparsers)
    return parser.parse_args()


def parse_input_numbers(s: str):
    options = []
    for option in re.split(", | ", s):
        match = re.search(r"(\d+)-(\d+)", option)
        if match:
            lower, upper = sorted([match.group(1), match.group(2)])
            options = options + list(range(int(lower), int(upper) + 1))
        else:
            try:
                options.append(int(option))
            except ValueError:
                pass
    return options


def extract_to_file(args):
    schema = extract(args)
    rich.print(f"\nWriting resulting schema to {args.out}...")
    with open(args.out, "w") as out:
        json.dump(schema, out, indent=4)
    rich.print("[green bold]Done![/green bold]")


def extract(args):
    rich.print(
        "\n[green bold]MongoDB[/green bold] -> [blue bold]CrateDB[/blue bold] Exporter :: Schema Extractor\n\n"
    )

    # Find collections
    client = pymongo.MongoClient(args.host, int(args.port))
    db = client[args.database]
    collections = db.list_collection_names(include_system_collections=False)
    a = {}

    tbl = rich.table.Table(show_header=True, header_style="bold blue")
    tbl.add_column("Id", width=3)
    tbl.add_column("Collection Name")
    tbl.add_column("Estimated Size")

    for i, c in enumerate(collections):
        tbl.add_row(str(i), c, str(db[c].estimated_document_count()))

    rich.print(tbl)

    rich.print("\nCollections to exclude: (eg: '0 1 2', '0, 1, 2', '0-2')")

    collections_to_ignore = parse_input_numbers(input("> "))
    filtered_collections = []
    for i, c in enumerate(collections):
        if i not in collections_to_ignore:
            filtered_collections.append(c)

    if filtered_collections == []:
        rich.print("\nExcluding all collections. Nothing to do.")
        exit(0)

    rich.print("\nDo a [red bold]full[/red bold] collection scan?")
    rich.print(
        "A full scan will iterate over all documents in the collection, a partial only one document. (Y/n)"
    )
    full = input(">  ").strip().lower()

    partial = full != "y"

    rich.print(
        f"\nExecuting a [red bold]{'partial' if partial else 'full'}[/red bold] scan..."
    )
    for collection in filtered_collections:
        a[collection] = extract_schema_from_collection(db[collection], partial)
    return a


def translate(d):
    rich.print(
        "\n[green bold]MongoDB[/green bold] -> [blue bold]CrateDB[/blue bold] Exporter :: Schema Extractor\n\n"
    )
    tran(d)


def translate_from_file(args):
    import json

    with open(args.infile) as f:
        o = json.load(f)
        translate(o)


def main():
    args = get_args()
    if args.command == "extract":
        extract_to_file(args)
    elif args.command == "translate":
        translate_from_file(args)
    elif args.command == "full":
        d = extract(args)
        translate(d)


if __name__ == "__main__":
    main()
