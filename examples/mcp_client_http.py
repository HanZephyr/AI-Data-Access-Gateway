import argparse
import json
from typing import Any
from urllib import request


def call_tool(base_url: str, api_key: str, tool_name: str, payload: dict[str, Any]) -> Any:
    body = json.dumps(payload).encode()
    http_request = request.Request(
        f"{base_url.rstrip('/')}/mcp/tools/{tool_name}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-ADG-API-Key": api_key,
        },
    )
    with request.urlopen(http_request, timeout=10) as response:
        return json.loads(response.read().decode())


def main() -> None:
    parser = argparse.ArgumentParser(description="Call ADG MCP-style HTTP tools.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", default="adg_admin")
    parser.add_argument("--user-id", default="demo-user")
    args = parser.parse_args()

    identity = {"user_id": args.user_id}
    datasources = call_tool(args.base_url, args.api_key, "list_datasources", identity)
    print(json.dumps({"list_datasources": datasources}, indent=2))

    datasource_id = datasources["datasources"][0]["id"]
    resources = call_tool(
        args.base_url,
        args.api_key,
        "list_resources",
        {**identity, "datasource_id": datasource_id},
    )
    print(json.dumps({"list_resources": resources}, indent=2))

    resource_id = resources["resources"][0]["id"]
    description = call_tool(
        args.base_url,
        args.api_key,
        "describe_resource",
        {**identity, "resource_id": resource_id},
    )
    print(json.dumps({"describe_resource": description}, indent=2))


if __name__ == "__main__":
    main()
