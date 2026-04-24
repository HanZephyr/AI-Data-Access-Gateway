import { describe, expect, it } from "vitest";

import { findTreePathByKey } from "./catalogNavigation";

describe("findTreePathByKey", () => {
  it("returns the full ancestor path for nested catalog nodes", () => {
    const tree = [
      {
        key: "datasource:ds_1",
        children: [
          {
            key: "resource:db_1",
            children: [
              {
                key: "resource:schema_1",
                children: [{ key: "resource:table_1", children: [] }],
              },
            ],
          },
        ],
      },
    ];

    expect(findTreePathByKey(tree, "resource:table_1")).toEqual([
      "datasource:ds_1",
      "resource:db_1",
      "resource:schema_1",
      "resource:table_1",
    ]);
  });

  it("returns an empty path when the target key does not exist", () => {
    expect(findTreePathByKey([{ key: "datasource:ds_1", children: [] }], "resource:missing")).toEqual([]);
  });
});
