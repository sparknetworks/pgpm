pgpm |build-status|
===================
``pgpm`` is a package manager for Postgres database.
Its main features include deployment of postgres objects (schemas, tables, functions, etc.), tracking of DDL changes and execution of arbitrary scripts across multiple data sources.

Installation
------------
Prerequisites: Postgres 9.4+, python 2.7/3.4+.

1) Install ``psycopg2``. This cannot be easily resolved with ``pip`` as the library relies on Postgres binaries. The step is not always trivial, though Google will certainly enlighten the path.
2) Run

.. code-block:: bash

    $ pip install pgpm

3) Install pgpm in every postgres database you'll be using with pgpm (must be a superuser). E.g.:

.. code-block:: bash

    $ pgpm install "postgresql://postgres:postgres@localhost:5432/testdb"

Note: connection string must conform `libpg format <https://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNSTRING>`_.

Main concepts
-------------
Package
```````
In ``pgpm`` a package is a set of files in a directory with valid ``config.json`` (see below) file. When package is being deployed, ``pgpm`` reads the configuration and executes sql scripts from files specified in the package configuration.
Note: ``config.json`` file must be present in a root directory of the package in order to use deployment feature of pgpm

Config
``````
``pgpm`` uses config.json file for a configuration of a package. Configuration file must be a single valid JSON object with the following properties:

===============  ===================  ============  =============
 Property name    Required/Optional    Value         Description
===============  ===================  ============  =============
 ``name``         required             ``string``    Name of the package
===============  ===================  ============  =============

Scope of package
''''''''''''''''
TODO

Object types
''''''''''''
TODO

General config
``````````````
TODO

Main features
-------------
Package deployment
``````````````````
TODO

DDL change logging
``````````````````
TODO

pgpm schema
```````````
TODO

TODOs
-----
- Provide support for DDL evolutions and dependency management.

.. |build-status| image:: https://travis-ci.org/affinitas/pgpm.svg?branch=develop
   :target: https://travis-ci.org/affinitas/pgpm
   :alt: Build status

