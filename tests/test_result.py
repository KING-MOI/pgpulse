from pgpulse.result import plural


def test_plural():
    assert plural(1, "table") == "1 table"
    assert plural(2, "table") == "2 tables"
    assert plural(1, "query", "queries") == "1 query"
    assert plural(0, "query", "queries") == "0 queries"
    assert plural(12_000, "deadlock") == "12,000 deadlocks"
