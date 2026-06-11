# pgpulse

[![ci](https://github.com/OWNER/pgpulse/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/pgpulse/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Health checks for Postgres from the command line. pgpulse connects to a
database, runs a set of checks and prints a color-coded report. It exits
non-zero when something is wrong, so it drops straight into cron jobs and CI.

## Install

```sh
pip install pgpulse
```

## Usage

```sh
pgpulse --dsn "postgresql://user@localhost/app"
```

Without `--dsn`, pgpulse reads `PGPULSE_DSN`. If that is unset too, libpq
falls back to the usual `PGHOST`, `PGUSER`, `PGDATABASE` and friends.

Run a subset of checks:

```sh
pgpulse --dsn "$DATABASE_URL" --check cache_hit --check connections
```

List what is available:

```sh
pgpulse --list-checks
```

## Checks

| check | what it looks at |
|-------|------------------|
| `cache_hit` | share of table reads served from shared buffers |
| `connections` | client connections versus `max_connections` |
| `long_queries` | active queries running past a time limit |
| `idle_in_transaction` | sessions sitting in an open transaction |
| `blocking_locks` | sessions stuck behind another session's lock |
| `bloat` | tables with a high share of dead tuples |
| `vacuum_age` | tables with dead tuples that vacuum has not reached |
| `xid_wraparound` | transaction ID age per database |
| `unused_indexes` | non-unique indexes with zero scans |
| `invalid_indexes` | indexes left behind by a failed concurrent build |
| `duplicate_indexes` | indexes with identical definitions |
| `index_usage` | large tables read mostly by sequential scan |
| `replication_lag` | replay lag of standbys, or of this standby |
| `replication_slots` | inactive slots and the WAL they retain |
| `sequences` | sequences close to their limit, including the column type |

## Exit codes

| code | meaning |
|------|---------|
| 0 | every check passed or only warned (see `--fail-on warn`) |
| 1 | at least one check failed or errored |
| 2 | bad config file |
| 3 | could not connect to the database |

## License

MIT
