#!/bin/bash
set -em

docker-entrypoint.sh postgres &
[[ -n $POSTGRES_DB ]] && sleep 10s && pgxn --verbose load --yes -U $POSTGRES_USER -d $POSTGRES_DB /tmp/h3-unreleased.zip
fg
