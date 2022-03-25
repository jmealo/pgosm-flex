# PgOSM-Flex Standard Import

These instructions show how to manually run the PgOSM-Flex process.
This is the best option for scaling to larger regions (North America, Europe, etc.)
due to the need to customize a number of configurations.  Review the
`python3 docker/pgosm_flex.py` for a starting point to automating the process.

This basic working example uses Washington D.C. for a small, fast test of the
process.


## Ubuntu Pre-reqs

This section covers installation of prerequisites required to install Postgres,
osm2pgsql, and PgOSM-Flex on Ubuntu 20.04.

```bash
sudo apt update
sudo apt install -y \
        sqitch wget curl ca-certificates \
        git make cmake g++ \
        libboost-dev libboost-system-dev \
        libboost-filesystem-dev libexpat1-dev zlib1g-dev \
        libbz2-dev libpq-dev libproj-dev lua5.2 liblua5.2-dev \
        unzip
```

LuaRocks is installed from source to ensure the latest version is available. Instructions
[from luarocks.org](https://luarocks.org/).


```bash
wget https://luarocks.org/releases/luarocks-3.8.0.tar.gz
tar zxpf luarocks-3.8.0.tar.gz
cd luarocks-3.8.0
./configure && make && sudo make install
```

Use `luarocks` to install `inifile` and `luasql-postgres`.


```bash
sudo luarocks install inifile
sudo luarocks install luasql-postgres PGSQL_INCDIR=/usr/include/postgresql/
```

Install osm2pgsql from source.  The version from `apt install` is unlikely to be new enough
for use with this project.


```bash
git clone git://github.com/openstreetmap/osm2pgsql.git
mkdir osm2pgsql/build
cd osm2pgsql/build
cmake ..
make
sudo make install
```

Add PGDG repo and install Postgres.  More [on Postgres Wiki](https://wiki.postgresql.org/wiki/Apt).

```bash
curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add - 
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
sudo apt-get update
sudo apt-get install postgresql-13 \
    postgresql-13-postgis-3 \
    postgresql-13-postgis-3-scripts
```

See the [osm2pgsql documentation](https://osm2pgsql.org/doc/manual.html#preparing-the-database) for advice on tuning Postgres configuration
for running osm2pgsql and Postgres on the same host.


## Download data

Download the PBF file and MD5 from Geofabrik.

```bash
mkdir ~/pgosm-data
cd ~/pgosm-data
wget https://download.geofabrik.de/north-america/us/district-of-columbia-latest.osm.pbf
wget https://download.geofabrik.de/north-america/us/district-of-columbia-latest.osm.pbf.md5
```

Verify integrity of the downloaded PBF file using `md5sum -c`.

```bash
md5sum -c district-of-columbia-latest.osm.pbf.md5
district-of-columbia-latest.osm.pbf: OK
```

## Prepare database

The typical use case is to run osm2pgsql and Postgres/PostGIS on the same node.
When using Postgres locally, only add the database name to the connection strings.


```bash
export PGOSM_CONN_PG="postgres"
export PGOSM_CONN="pgosm"
```

To run with a non-local Postgres connection, use a connection string such as:

```bash
export PGOSM_CONN_PG="postgresql://your_user:password@your_postgres_host/postgres"
export PGOSM_CONN="postgresql://your_user:password@your_postgres_host/pgosm"
```

Create the `pgosm` database.

```bash
psql -d $PGOSM_CONN_PG -c "CREATE DATABASE pgosm;"
```

Create the `postgis` extension and the `osm` schema.

```bash
psql -d $PGOSM_CONN -c "CREATE EXTENSION postgis; CREATE SCHEMA osm;"
```

See [POSTGRES-PERMISSIONS.md](POSTGRES-PERMISSIONS.md) for more about
permissions required by PgOSM Flex to run.


## Prepare PgOSM-Flex

The PgOSM-Flex styles from this project are required to run the following.
Clone the repo and change into the directory containing
the `.lua` and `.sql` scripts.


```bash
mkdir ~/git
cd ~/git
git clone https://github.com/rustprooflabs/pgosm-flex.git
cd pgosm-flex/flex-config
```


## Set PgOSM variables

*(Recommended)* 

Set the `PGOSM_DATE` and `PGOSM_REGION` env vars to indicate the
date and region of the downloaded OpenStreetMap data.
This data is saved in the `osm.pgosm_flex` table to allow end users in the resulting
data to know what each dataset should contain.


```bash
export PGOSM_DATE='2021-03-14'
export PGOSM_REGION='north-america/us--district-of-columbia'
```

These values show up in the `osm.pgosm_flex` table.

```sql
SELECT osm_date, region FROM osm.pgosm_flex;
```

```bash
┌────────────┬────────────────────────────────────────┐
│  osm_date  │                 region                 │
╞════════════╪════════════════════════════════════════╡
│ 2021-03-14 │ north-america/us--district-of-columbia │
└────────────┴────────────────────────────────────────┘
```

> Note:  See the [Customize PgOSM on the main README.md](https://github.com/rustprooflabs/pgosm-flex#customize-pgosm) for all runtime customization options.


## Run osm2pgsql w/ PgOSM-Flex

The `run-all.lua` script provides the most complete set of OpenStreetMap
data.  The list of main tables in PgOSM-Flex will continue to grow and evolve.



```bash
cd pgosm-flex/flex-config

osm2pgsql --output=flex --style=./run.lua \
    -d $PGOSM_CONN \
    ~/pgosm-data/district-of-columbia-latest.osm.pbf
```

## Run post-processing SQL

Each `.lua` script as an associated `.sql` script to create 
primary keys, indexes, comments, views and more.


```bash
lua ./run-sql.lua
```

> Note: The `run-all` scripts exclude `unitable` and `road_major`.

## Config Layerset

Define `PGOSM_LAYERSET` to override the use of `layerset/default.ini`.

```bash
export PGOSM_LAYERSET=everything
```

To define a path to custom layersets outside the standard path
set the `PGOSM_LAYERSET_PATH` env var.

NOTE: Include the trailing slash!

```bash
export PGOSM_LAYERSET_PATH=/custom-layerset/
```

Read more about layersets in [LAYERSETS.md](LAYERSETS.md).



## Generated nested place polygons

*(Recommended)*

The post-processing SQL scripts create a procedure to calculate the nested place polygon data.  It does not run by default in the previous step because it can be expensive (slow) on large regions.


```bash
psql -d $PGOSM_CONN -c "CALL osm.populate_place_polygon_nested();"
psql -d $PGOSM_CONN -c "CALL osm.build_nested_admin_polygons();"
```


# More options




## Additional structure and helper data

**Optional**

Deploying the additional table structure is done via [sqitch](https://sqitch.org/).

Assumes this repo is cloned under `~/git/pgosm-flex/` and a local Postgres
DB named `pgosm` has been created with the `postgis` extension installed.

```bash
cd ~/git/pgosm-flex/db
sqitch deploy db:pg:pgosm
```

With the structures created, load helper road data.

```bash
cd ~/git/pgosm-flex/db
psql -d pgosm -f data/roads-us.sql
```


Currently only U.S. region drafted, more regions with local `maxspeed` are welcome via PR!


## Customize PgOSM Flex

Track additional details in the `osm.pgosm_meta` table (see more below)
and customize behavior with the use of environment variables.

* `OSM_DATE`
* `PGOSM_SRID`
* `PGOSM_REGION`
* `PGOSM_LANGUAGE`


### Custom SRID

To use `SRID 4326` instead of the default `SRID 3857`, set the `PGOSM_SRID`
environment variable before running osm2pgsql.

```bash
export PGOSM_SRID=4326
```

Changes to the SRID are reflected in output printed.

```bash
2021-01-08 15:01:15  osm2pgsql version 1.4.0 (1.4.0-72-gc3eb0fb6)
2021-01-08 15:01:15  Database version: 13.1 (Ubuntu 13.1-1.pgdg20.10+1)
2021-01-08 15:01:15  Node-cache: cache=800MB, maxblocks=12800*65536, allocation method=11
Custom SRID: 4326
...
```

### Preferred Language

The `name` column throughout PgOSM-Flex defaults to using the highest priority
name tag according to the [OSM Wiki](https://wiki.openstreetmap.org/wiki/Names). Setting `PGOSM_LANGUAGE` allows giving preference to name tags with the
given language.
The value of `PGOSM_LANGUAGE` should match the codes used by OSM:

> where code is a lowercase language's ISO 639-1 alpha2 code, or a lowercase ISO 639-2 code if an ISO 639-1 code doesn't exist." -- [Multilingual names on OSM Wiki](https://wiki.openstreetmap.org/wiki/Multilingual_names)


```bash
export PGOSM_LANGUAGE=kn
```


## Troubleshooting

There are a lot of moving parts in this process.
This section is a collection of troubleshooting notes related to running PgOSM Flex
and osm2pgsql manually.


### Error in osm2pgsql processing

A variety of issues can create problems in the osm2pgsql processing step.
The following is a generic list of things to check for the most common issues.
Please check the [documentation on osm2pgsql.org](https://osm2pgsql.org/) for
the latest documented functionality.

* Check `osm2pgsql --version`, typically the latest version is assumed
* Does your `.osm.pbf` file exist in the correct location?
* Does the database user have proper [permissisions in Postgres](POSTGRES-PERMISSIONS.md)?



### Too many Postgres connections

Using osm2pgsql opens a number of connections to the Postgres database. The
number of connections opened depends on two factors:  # of tables, and create/update mode.
You know you have encountered this problem if you get an error message such as
`ERROR: Connecting to database failed: connection to server at "localhost" (127.0.0.1), port 5432 failed: FATAL:  sorry, too many clients already`.


The osm2pgsql docs [document the number of connections](https://osm2pgsql.org/doc/manual.html#number-of-connections).  PgOSM Flex's default layerset creates 41
tables.  This means running in create mode (fresh import) will require at least
44 connections to Postgres.  Update mode (via `osm2pgsql-replication`) creates
a minimum of 208 connections to Postgres.


Using [pgBouncer](https://www.pgbouncer.org/) or another connection pool
in front of Postgres is recommended.


