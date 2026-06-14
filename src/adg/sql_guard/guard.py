from dataclasses import dataclass, field
from typing import cast

import sqlglot
from sqlglot import exp


@dataclass(frozen=True)
class SqlGuardResult:
    """Structured verdict produced after parsing and normalizing a SQL statement."""

    allowed: bool
    normalized_sql: str | None
    statement_type: str | None
    accessed_resources: list[str] = field(default_factory=list)
    accessed_fields: list[str] = field(default_factory=list)
    used_functions: list[str] = field(default_factory=list)
    risk_level: str = "high"
    rejection_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class SqlGuard:
    """Conservative SQL allowlist for read-only runtime query execution."""

    allowed_functions = {"count", "sum", "avg", "min", "max"}
    _safe_temporal_cast_types = (
        exp.DataType.Type.DATE,
        exp.DataType.Type.DATE32,
        exp.DataType.Type.DATETIME,
        exp.DataType.Type.DATETIME2,
        exp.DataType.Type.DATETIME64,
        exp.DataType.Type.SMALLDATETIME,
        exp.DataType.Type.TIME,
        exp.DataType.Type.TIMETZ,
        exp.DataType.Type.TIME_NS,
        exp.DataType.Type.TIMESTAMP,
        exp.DataType.Type.TIMESTAMPNTZ,
        exp.DataType.Type.TIMESTAMPLTZ,
        exp.DataType.Type.TIMESTAMPTZ,
        exp.DataType.Type.TIMESTAMP_S,
        exp.DataType.Type.TIMESTAMP_MS,
        exp.DataType.Type.TIMESTAMP_NS,
    )

    def __init__(self, *, default_limit: int = 100, max_limit: int = 1000) -> None:
        """Configure the default and maximum row limits applied to accepted queries."""

        self._default_limit = default_limit
        self._max_limit = max_limit

    def check(self, sql: str) -> SqlGuardResult:
        """Parse, validate, and normalize a single read-only SQL statement."""

        try:
            statements = [
                cast(exp.Expression, statement)
                for statement in sqlglot.parse(sql)
                if statement is not None
            ]
        except sqlglot.errors.SqlglotError as error:
            return SqlGuardResult(
                allowed=False,
                normalized_sql=None,
                statement_type=None,
                rejection_reasons=[f"parse_error:{error.__class__.__name__}"],
            )

        if len(statements) != 1:
            return SqlGuardResult(
                allowed=False,
                normalized_sql=None,
                statement_type=None,
                rejection_reasons=["multiple_statements"],
            )

        statement = statements[0]
        statement_type = statement.key.upper()
        # V1 intentionally accepts only SELECT-shaped AST nodes; mutation and DDL are rejected.
        if not isinstance(statement, exp.Select):
            return SqlGuardResult(
                allowed=False,
                normalized_sql=None,
                statement_type=statement_type,
                accessed_resources=self._accessed_resources(statement),
                accessed_fields=self._accessed_fields(statement),
                rejection_reasons=["statement_not_allowed"],
            )

        used_functions = self._used_functions(statement)
        # Function allowlisting keeps expensive or unsafe database functions out of runtime SQL.
        rejection_reasons = [
            f"function_not_allowed:{function_name}"
            for function_name in used_functions
            if function_name not in self.allowed_functions
        ]
        if self._has_wildcard_projection(statement):
            rejection_reasons.append("wildcard_projection_not_allowed")
        normalized_sql, warnings = self._with_effective_limit(statement)

        return SqlGuardResult(
            allowed=not rejection_reasons,
            normalized_sql=normalized_sql if not rejection_reasons else None,
            statement_type="SELECT",
            accessed_resources=self._accessed_resources(statement),
            accessed_fields=self._accessed_fields(statement),
            used_functions=used_functions,
            risk_level="low" if not rejection_reasons else "high",
            rejection_reasons=rejection_reasons,
            warnings=warnings,
        )

    def _with_effective_limit(self, statement: exp.Select) -> tuple[str, list[str]]:
        """Return SQL with a bounded LIMIT and warnings describing limit changes."""

        warnings: list[str] = []
        current_limit = self._limit_value(statement)
        effective_limit = self._default_limit if current_limit is None else current_limit
        if effective_limit > self._max_limit:
            effective_limit = self._max_limit
            warnings.append("limit_reduced_to_max")
        elif current_limit is None:
            warnings.append("default_limit_applied")

        limited = statement.copy()
        limited.set("limit", exp.Limit(expression=exp.Literal.number(effective_limit)))
        return limited.sql(), warnings

    def _limit_value(self, statement: exp.Select) -> int | None:
        """Extract a literal LIMIT or treat non-literal limits as the configured maximum."""

        limit = statement.args.get("limit")
        if not isinstance(limit, exp.Limit):
            return None
        expression = limit.expression
        if isinstance(expression, exp.Literal) and expression.is_int:
            return int(expression.this)
        return self._max_limit

    def _accessed_resources(self, statement: exp.Expression) -> list[str]:
        """Collect referenced table names for later resource-policy resolution."""

        resources = {
            ".".join(part for part in (table.db, table.name) if part)
            for table in statement.find_all(exp.Table)
        }
        return sorted(resources)

    def _accessed_fields(self, statement: exp.Expression) -> list[str]:
        """Collect referenced column names for audit metadata."""

        fields = {column.name for column in statement.find_all(exp.Column) if column.name != "*"}
        return sorted(fields)

    def _used_functions(self, statement: exp.Expression) -> list[str]:
        """Collect SQL function names used by the statement."""

        names: set[str] = set()
        for function in statement.find_all(exp.Func):
            if self._is_safe_builtin_expression(function):
                continue
            sql_name = function.sql_name().lower()
            if sql_name:
                names.add(sql_name)
        return sorted(names)

    def _is_safe_builtin_expression(self, function: exp.Func) -> bool:
        """Skip sqlglot function-shaped nodes that are safe SQL operators or literals."""

        if isinstance(
            function,
            (
                exp.And,
                exp.Or,
                exp.CurrentDate,
                exp.CurrentTime,
                exp.CurrentTimestamp,
            ),
        ):
            return True
        if isinstance(function, exp.Cast):
            return self._is_safe_temporal_literal_cast(function)
        return False

    def _is_safe_temporal_literal_cast(self, function: exp.Cast) -> bool:
        """Allow DATE/TIME/TIMESTAMP literal syntax without opening arbitrary casts."""

        target = function.to
        return (
            isinstance(function.this, exp.Literal)
            and isinstance(target, exp.DataType)
            and target.is_type(*self._safe_temporal_cast_types)
        )

    def _has_wildcard_projection(self, statement: exp.Select) -> bool:
        """Reject wildcard projections so runtime callers must name fields explicitly."""

        return any(
            isinstance(projection, exp.Star)
            or (
                isinstance(projection, exp.Column)
                and isinstance(projection.this, exp.Star)
            )
            for projection in statement.expressions
        )
