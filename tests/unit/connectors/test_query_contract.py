from adg.connectors.base import QueryResult


def test_query_result_is_ai_friendly_mapping_shape() -> None:
    result = QueryResult(
        columns=[{"name": "id", "data_type": "integer"}],
        rows=[{"id": 1}],
    )

    assert result.columns == [{"name": "id", "data_type": "integer"}]
    assert result.rows == [{"id": 1}]
