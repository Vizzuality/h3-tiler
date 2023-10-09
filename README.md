# h3 Tiler

A simple tiler for h3 data.

This repo can be considered a _reference implementation_ of what is needed to build a h3 tile system.

Be warned that this repo is under heavy development and the approach of each part doesn't have to be the optimal one.

The important parts are:

```
├── deck                            <- The client app
│   ├── app.js
│   ├── h3-tile-layer.js            <- The deck.gl custom layer for h3 tiles
│   ├── index.html
│   └── package.json
├── src                             <- The tiler app done in FastAPI
│   └── h3tiler
│       ├── main.py                 <- FastAPI entrypoint
│       ├── config.py               <- Settings and env stuff
│       ├── rounting.py             <- API endpoints
│       └── adapters
│           └── postgres.py         <- Adapter for getting data from a postgres database
├── db
│   └── Dockerfile                  <- Dockerfile for the postgres database
│
├── scripts
│   ├── raster_to_h3.py             <- Script for creating the h3 data from a file
│   └── h3_file_to_db_table.py      <- Copy the h3 data from a file to a postgres table
│
├── docker-compose.yml              <- Spin it all up
.
.
.
```

## Usage

### Docker
just do

```bash
docker compose up --build
```

then run the scripts in `scripts/` to populate the database.

### Local

To run the client in `deck/` run:

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
