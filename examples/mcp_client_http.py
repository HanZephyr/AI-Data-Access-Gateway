import argparse
import json
import sys
from typing import Any
from urllib import error, request


def call_tool(base_url: str, api_key: str, tool_name: str, payload: dict[str, Any]) -> Any:
    """Call one ADG simple HTTP runtime tool and decode its JSON response."""

    body = json.dumps(payload).encode()
    http_request = request.Request(
        f"{base_url.rstrip('/')}/api/tools/{tool_name}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-ADG-API-Key": api_key,
        },
    )
    try:
        with request.urlopen(http_request, timeout=10) as response:
            return json.loads(response.read().decode())
    except error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        message = body_text or exc.reason
        raise SystemExit(f"HTTP {exc.code} calling {tool_name}: {message}") from exc


def main() -> None:
    """Run a tiny discovery flow against the current simple HTTP tool route."""

    parser = argparse.ArgumentParser(
        description=(
            "Call ADG simple HTTP runtime tools. Runtime identity comes from the bound API key."
        )
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()

    datasources = call_tool(args.base_url, args.api_key, "list_datasources", {})
    print(json.dumps({"list_datasources": datasources}, indent=2))

    datasource_items = datasources.get("datasources", [])
    if not datasource_items:
        raise SystemExit("No visible datasources returned by list_datasources.")

    datasource_id = datasource_items[0]["id"]
    resources = call_tool(
        args.base_url,
        args.api_key,
        "list_resources",
        {"datasource_id": datasource_id},
    )
    print(json.dumps({"list_resources": resources}, indent=2))

    resource_items = resources.get("resources", [])
    if not resource_items:
        raise SystemExit("No visible resources returned by list_resources.")

    resource_id = resource_items[0]["id"]
    description = call_tool(
        args.base_url,
        args.api_key,
        "describe_resource",
        {"resource_id": resource_id},
    )
    print(json.dumps({"describe_resource": description}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
