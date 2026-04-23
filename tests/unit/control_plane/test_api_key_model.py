from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey


def test_api_key_model_is_registered() -> None:
    assert "api_keys" in Base.metadata.tables
    assert ApiKey.__tablename__ == "api_keys"
