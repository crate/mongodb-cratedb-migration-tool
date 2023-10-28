# -*- coding: utf-8; -*-
#
# Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  Crate licenses
# this file to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may
# obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
# However, if you have executed another commercial license agreement
# with Crate these terms will supersede the license and you may use the
# software solely pursuant to the terms of the relevant commercial agreement.

import argparse
import json

import pymongo
import rich
from rich.columns import Columns
from rich.syntax import Syntax

import re

from .extract import extract_schema_from_collection
from .translate import translate as translate_schema
from .export import export

from bson.raw_bson import RawBSONDocument


def extract_parser(subargs):
    parser = subargs.add_parser(
        "extract", help="Extract a schema from a MongoDB database"
    )
    parser.add_argument("--host", default="localhost", help="MongoDB host")
    parser.add_argument("--port", default=27017, help="MongoDB port")
    parser.add_argument("--database", required=True, help="MongoDB database")
    parser.add_argument(
        "--collection", help="MongoDB collection to create a schema for"
    )
    parser.add_argument(
        "--scan",
        choices=["full", "partial"],
        help="Whether to fully scan the MongoDB collections or only partially.",
    )
    parser.add_argument("-o", "--out", default="mongodb_schema.json")


def translate_parser(subargs):
    parser = subargs.add_parser(
        "translate",
        help="Translate a MongoDB schema definition to a CrateDB table schema",
    )
    parser.add_argument(
        "-i", "--infile", help="The JSON file to read the MongoDB schema from"
    )


def export_parser(subargs):
    parser = subargs.add_parser("export")
    parser.add_argument("--collection", required=True)
    parser.add_argument("--host", default="localhost", help="MongoDB host")
    parser.add_argument("--port", default=27017, help="MongoDB port")
    parser.add_argument("--database", required=True, help="MongoDB database")


def get_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    extract_parser(subparsers)
    translate_parser(subparsers)
    export_parser(subparsers)
    return parser.parse_args()


def parse_input_numbers(s: str):
    """ Parse an input string for numbers and ranges.

    Supports strings like '0 1 2', '0, 1, 2' as well as ranges such as
    '0-2'.
    """

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
    """ Extract a schema (or set of schemas) from MongoDB collections to a
    a JSON file.
    """

    schema = extract(args)
    rich.print(f"\nWriting resulting schema to {args.out}...")
    with open(args.out, "w") as out:
        json.dump(schema, out, indent=4)
    rich.print("[green bold]Done![/green bold]")


def gather_collections(database):
    """ Gather a list of collections to use from a MongoDB database, based
    on user input.
    """

    collections = database.list_collection_names(include_system_collections=False)

    tbl = rich.table.Table(show_header=True, header_style="bold blue")
    tbl.add_column("Id", width=3)
    tbl.add_column("Collection Name")
    tbl.add_column("Estimated Size")

    for i, c in enumerate(collections):
        tbl.add_row(str(i), c, str(database[c].estimated_document_count()))

    rich.print(tbl)

    rich.print("\nCollections to exclude: (eg: '0 1 2', '0, 1, 2', '0-2')")

    collections_to_ignore = parse_input_numbers(input("> "))
    filtered_collections = []
    for i, c in enumerate(collections):
        if i not in collections_to_ignore:
            filtered_collections.append(c)

    # MongoDB 2 does not understand `include_system_collections=False`.
    if "system.indexes" in filtered_collections:
        filtered_collections.remove("system.indexes")

    return filtered_collections


def extract(args):
    """ Extract schemas from MongoDB collections.

    This asks the user for which collections they would like to extract,
    iterates over these collections and returns a dictionary of schemas for
    each of the selected collections.
    """

    rich.print(
        "\n[green bold]MongoDB[/green bold] -> [blue bold]CrateDB[/blue bold] Exporter :: Schema Extractor\n\n"
    )

    client = pymongo.MongoClient(args.host, int(args.port))
    db = client[args.database]
    if args.collection:
        filtered_collections = [args.collection]
    else:
        filtered_collections = gather_collections(db)

    if filtered_collections == []:
        rich.print("\nExcluding all collections. Nothing to do.")
        exit(0)

    if args.scan:
        partial = args.scan == "partial"
    else:
        rich.print("\nDo a [red bold]full[/red bold] collection scan?")
        rich.print(
            "A full scan will iterate over all documents in the collection, a partial only one document. (Y/n)"
        )
        full = input(">  ").strip().lower()

        partial = full != "y"

        rich.print(
            f"\nExecuting a [red bold]{'partial' if partial else 'full'}[/red bold] scan..."
        )

    schemas = {}
    for collection in filtered_collections:
        schemas[collection] = extract_schema_from_collection(db[collection], partial)
    return schemas


def translate(schema):
    """Translates a given schema into a CrateDB compatable CREATE TABLE SQL
    statement.
    """
    rich.print(
        "\n[green bold]MongoDB[/green bold] -> [blue bold]CrateDB[/blue bold] Exporter :: Schema Extractor\n\n"
    )
    sql_queries = translate_schema(schema)
    for collection, query in sql_queries.items():
        syntax = Syntax(query, "sql")
        rich.print(f"Collection [blue bold]'{collection}'[/blue bold]:")
        rich.print(syntax)
        rich.print()


def translate_from_file(args):
    """ Reads in a JSON file and extracts the schema from it."""

    with open(args.infile) as f:
        schema = json.load(f)
        translate(schema)


def export_to_stdout(args):
    client = pymongo.MongoClient(
        args.host, int(args.port), document_class=RawBSONDocument
    )
    db = client[args.database]
    export(db[args.collection])


def main():
    args = get_args()
    if args.command == "extract":
        extract_to_file(args)
    elif args.command == "translate":
        translate_from_file(args)
    elif args.command == "export":
        export_to_stdout(args)


if __name__ == "__main__":
    main()
