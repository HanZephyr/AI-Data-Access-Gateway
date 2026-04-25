from adg.control_plane.imports.connectors.base import DirectoryImporter, PullOnlyDirectoryImporter
from adg.control_plane.imports.connectors.dingtalk import DingTalkImporter
from adg.control_plane.imports.connectors.feishu import FeishuImporter
from adg.control_plane.imports.connectors.wecom import WeComImporter

CONNECTOR_REGISTRY: dict[str, type[PullOnlyDirectoryImporter]] = {
    "feishu": FeishuImporter,
    "wecom": WeComImporter,
    "dingtalk": DingTalkImporter,
}


def get_directory_importer(platform: str) -> DirectoryImporter:
    """Instantiate a supported pull-only importer by platform slug."""

    importer_class = CONNECTOR_REGISTRY.get(platform)
    if importer_class is None:
        raise ValueError(f"Unsupported importer platform: {platform}")
    return importer_class()
