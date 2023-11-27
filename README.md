# h3 Tiler

A simple tiler for h3 data.

This repo can be considered a _reference implementation_ of what is needed to build a h3 tile system.

Be warned that this repo is under heavy development and the approach of each part doesn't have to be the optimal one.

The important parts are:

```
.
├── db                              <- Postgres DB setup example
├── demo                            <- Demo client app
├── h3tile-layer                    <- deck.gl custom layer module
├── scripts
│   ├── raster_to_h3.py             <- Script for creating the h3 data from a file
│   └── h3_file_to_db_table.py      <- Copy the h3 data from a file to a postgres table
├── src                             <- The tiler service done in FastAPI
│   └── h3tiler
│       └── adapters                <- Adapter for getting data from a postgres database
│
├── docker-compose.yml              <- Spin it all up
...
```

## Usage

### Docker

just do

```bash
docker compose up --build
```

then run the scripts in `scripts/` to populate the database.

### Local Demo

To run the client in `demo/` run:

```bash
npm install
```

then:

```bash
npm start
```

to spin the tiler, in `src/`, run:

```bash
python -m uvicorn h3tiler.main:app --reload
```
