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

Show only the checks that need attention:

```sh
pgpulse --quiet
```

List what is available:

```sh
pgpulse --list-checks
```

### Markdown output

`--format markdown` renders a table with collapsible details, handy for a
GitHub Actions job summary:

```sh
pgpulse --format markdown >> "$GITHUB_STEP_SUMMARY"
```

### JSON output

`--format json` prints one object that is easy to feed into monitoring:

```json
{
  "server": "app on 10.0.0.5 (PostgreSQL 16.4, primary)",
  "status": "warn",
  "checks": [
    {
      "name": "bloat",
      "status": "warn",
      "summary": "1 bloated table",
      "details": ["public.events: 31% dead tuples"],
      "seconds": 0.0021
    }
  ]
}
```

`status` is one of `skip`, `ok`, `warn`, `fail` or `error`. The top-level
`status` is the worst of the checks.

## Configuration

Thresholds live in a TOML file. Every key is optional; anything left out
keeps its default. [`pgpulse.example.toml`](pgpulse.example.toml) lists all
of them.

```toml
dsn = "postgresql://pgpulse@db.internal/app"
exclude = ["primary_keys"]

[cache_hit]
warn = 0.98
fail = 0.9

[long_queries]
warn_seconds = 120
```

```sh
pgpulse --config pgpulse.toml
```

Unknown keys are rejected, so a typo fails loudly instead of being ignored.
Each check also runs under a `statement_timeout` (10s by default) so a
struggling server cannot hang the report.

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
| `xmin_horizon` | the session, prepared transaction or slot holding back vacuum |
| `unused_indexes` | non-unique indexes with zero scans |
| `invalid_indexes` | indexes left behind by a failed concurrent build |
| `duplicate_indexes` | indexes with identical definitions |
| `index_usage` | large tables read mostly by sequential scan |
| `replication_lag` | replay lag of standbys, or of this standby |
| `replication_slots` | inactive slots and the WAL they retain |
| `sequences` | sequences close to their limit, including the column type |
| `deadlocks` | deadlocks per day since stats were reset |
| `temp_files` | bytes spilled to temp files per day |
| `rollbacks` | share of transactions that roll back |
| `checkpoints` | share of checkpoints forced by WAL volume |
| `primary_keys` | tables without a primary key |
| `archiver` | whether WAL archiving is currently failing |

## Exit codes

| code | meaning |
|------|---------|
| 0 | every check passed or only warned (see `--fail-on warn`) |
| 1 | at least one check failed or errored |
| 2 | bad config file |
| 3 | could not connect to the database |

## License

MIT
