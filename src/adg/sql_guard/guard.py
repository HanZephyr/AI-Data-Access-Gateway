from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp


@dataclass(frozen=True)
class SqlGuardResult:
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
    allowed_functions = {"count", "sum", "avg", "min", "max"}

    def __init__(self, *, default_limit: int = 100, max_limit: int = 1000) -> None:
        self._default_limit = default_limit
        self._max_limit = max_limit

    def check(self, sql: str) -> SqlGuardResult:
        try:
            statements = [statement for statement in sqlglot.parse(sql) if statement is not None]
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
        rejection_reasons = [
            f"function_not_allowed:{function_name}"
            for function_name in used_functions
            if function_name not in self.allowed_functions
        ]
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
        limit = statement.args.get("limit")
        if not isinstance(limit, exp.Limit):
            return None
        expression = limit.expression
        if isinstance(expression, exp.Literal) and expression.is_int:
            return int(expression.this)
        return self._max_limit

    def _accessed_resources(self, statement: exp.Expression) -> list[str]:
        resources = {
            ".".join(part for part in (table.db, table.name) if part)
            for table in statement.find_all(exp.Table)
        }
        return sorted(resources)

    def _accessed_fields(self, statement: exp.Expression) -> list[str]:
        fields = {column.name for column in statement.find_all(exp.Column) if column.name != "*"}
        return sorted(fields)

    def _used_functions(self, statement: exp.Expression) -> list[str]:
        names: set[str] = set()
        for function in statement.find_all(exp.Func):
            sql_name = function.sql_name().lower()
            if sql_name:
                names.add(sql_name)
        return sorted(names)
