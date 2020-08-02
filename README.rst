MongoDB → CrateDB Schema Extractor
==================================

This tool iterates over a MongoDB collection (or series of collections) and
iteratively builds up a description of the schema of that collection. This
description can then be used to create a CrateDB schema, which will attempt
to determine a best-fit table definition for that schema.

As such, this means the tool works best on collections of similarly structured
and typed data.

Installation
------------

To install::

    $ python -m venv .venv
    $ source .venv/bin/activate
    $ pip install -e .


Schema Extraction
-----------------

To extract a description of the schema of a collection, you can use the `extract`
subcommand. For example::

    $ rip extract --host localhost --port 27017 --database test_db

This will connect to the MongoDB instance for the host:port. It will then look
at the collections within that database, and ask you which collections to
*exclude* from analysis.

You can then do a *full* or *partial* scan of the collection.

A partial scan will only look at the first entry in a collection, and thus
produce an unambigious schema definition, which is useful if you already know
the collection is systematically and regularly structured.

A full scan will iterate over the entire collection and build up the schema
description. Cancelling the scan will cause the tool to output the schema
description it has built up thus far.

For example, scanning a collection of payloads consisting of a `ts` field,
a `sensor` field and a `payload` object can result in this::

    {
        "test": {
            "count": 100000,
            "document": {
                "_id": {
                    "count": 100000,
                    "types": {
                        "OID": {
                            "count": 100000
                        }
                    }
                },
                "ts": {
                    "count": 100000,
                    "types": {
                        "DATETIME": {
                            "count": 100000
                        }
                    }
                },
                "sensor": {
                    "count": 100000,
                    "types": {
                        "STRING": {
                            "count": 100000
                        }
                    }
                },
                "payload": {
                    "count": 100000,
                    "types": {
                        "OBJECT": {
                            "count": 100000,
                            "document": {
                                "temp": {
                                    "count": 100000,
                                    "types": {
                                        "FLOAT": {
                                            "count": 1
                                        },
                                        "INTEGER": {
                                            "count": 99999
                                        }
                                    }
                                },
                                "humidity": {
                                    "count": 100000,
                                    "types": {
                                        "FLOAT": {
                                            "count": 1
                                        },
                                        "INTEGER": {
                                            "count": 99999
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

This description indicates that the data is well structured and has mostly
consistent data-types.

Translate Schema
----------------

Once a schema description has been extracted, this can be translated into a
CrateDB schema definition using the `translate` subcommand::

    $ rip translate -i mongodb_schema.json

This will attempt to translate the description into a best-fit CrateDB table
definition. Where datatypes are ambigious, it will *choose the most common
datatype*. For example, the above example would result in::

    CREATE TABLE IF NOT EXISTS "doc"."test" (
        "ts" TIMESTAMP WITH TIME ZONE,
        "sensor" TEXT,
        "payload" OBJECT (STRICT) AS (
            -- ⬇️ Types: FLOAT: 0.0%, INTEGER: 100.0%
            "temp" INTEGER,
            -- ⬇️ Types: FLOAT: 0.0%, INTEGER: 100.0%
            "humidity" INTEGER
        )
    );


Extract and Translate Schema
----------------------------

To do schema extraction and translation in one command, use the `full` subcommand::

    $ rip full --host localhost --port 27017 --database test_db

Test
----

To run the tests::

    $ python -m unittest
