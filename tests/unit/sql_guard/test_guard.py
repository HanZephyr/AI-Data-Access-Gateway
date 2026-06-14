from adg.sql_guard.guard import SqlGuard


def test_guard_allows_select_and_injects_default_limit() -> None:
    result = SqlGuard(default_limit=100, max_limit=500).check(
        "select id, name from public.customers"
    )

    assert result.allowed is True
    assert result.statement_type == "SELECT"
    assert result.normalized_sql is not None
    assert "LIMIT 100" in result.normalized_sql
    assert result.accessed_resources == ["public.customers"]
    assert result.accessed_fields == ["id", "name"]
    assert result.risk_level == "low"


def test_guard_reduces_limit_to_maximum() -> None:
    result = SqlGuard(default_limit=100, max_limit=500).check(
        "select id from public.customers limit 900"
    )

    assert result.allowed is True
    assert result.normalized_sql is not None
    assert "LIMIT 500" in result.normalized_sql


def test_guard_rejects_mutation_statement() -> None:
    result = SqlGuard().check("delete from public.customers where id = 1")

    assert result.allowed is False
    assert "statement_not_allowed" in result.rejection_reasons


def test_guard_rejects_multiple_statements() -> None:
    result = SqlGuard().check("select id from public.customers; select id from public.orders")

    assert result.allowed is False
    assert "multiple_statements" in result.rejection_reasons


def test_guard_rejects_select_star() -> None:
    result = SqlGuard().check("select * from public.customers")

    assert result.allowed is False
    assert result.normalized_sql is None
    assert "wildcard_projection_not_allowed" in result.rejection_reasons


def test_guard_rejects_qualified_wildcard() -> None:
    result = SqlGuard().check("select c.*, c.id from public.customers c")

    assert result.allowed is False
    assert result.normalized_sql is None
    assert "wildcard_projection_not_allowed" in result.rejection_reasons


def test_guard_rejects_non_whitelisted_functions() -> None:
    result = SqlGuard().check("select md5(email) from public.customers")

    assert result.allowed is False
    assert "function_not_allowed:md5" in result.rejection_reasons


def test_guard_allows_boolean_predicates() -> None:
    result = SqlGuard().check(
        "select id, total from public.orders "
        "where (status = 'paid' and total > 100) or status = 'refunded'"
    )

    assert result.allowed is True
    assert result.normalized_sql is not None
    assert result.used_functions == []
    assert "AND" in result.normalized_sql
    assert "OR" in result.normalized_sql


def test_guard_allows_common_date_predicates() -> None:
    result = SqlGuard().check(
        "select id from public.orders "
        "where created_at >= current_date - interval '30 days'"
    )

    assert result.allowed is True
    assert result.normalized_sql is not None
    assert result.used_functions == []


def test_guard_allows_date_literal_casts() -> None:
    result = SqlGuard().check(
        "select id from public.orders where created_at >= date '2026-05-15'"
    )

    assert result.allowed is True
    assert result.normalized_sql is not None
    assert result.used_functions == []


def test_guard_rejects_non_literal_casts() -> None:
    result = SqlGuard().check("select cast(email as text) from public.customers")

    assert result.allowed is False
    assert "function_not_allowed:cast" in result.rejection_reasons


def test_guard_allows_common_aggregate_functions() -> None:
    result = SqlGuard().check("select count(*), sum(total) from public.orders")

    assert result.allowed is True
    assert result.used_functions == ["count", "sum"]
