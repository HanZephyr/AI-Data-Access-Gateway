import { describe, expect, it } from "vitest";

import {
  buildDirectoryImportPayload,
  buildUserCreatePayload,
  normalizeOrgPathDelimiter,
  parseDirectoryRowsFromText,
} from "./directoryForms";

describe("directory import helpers", () => {
  it("defaults the organization delimiter to a slash", () => {
    expect(normalizeOrgPathDelimiter("")).toBe("/");
    expect(normalizeOrgPathDelimiter("   ")).toBe("/");
    expect(normalizeOrgPathDelimiter(" :: ")).toBe("::");
  });

  it("parses spreadsheet-like csv rows into the backend import template", () => {
    expect(
      parseDirectoryRowsFromText(
        [
          "user_name,org_path,external_ref,roles",
          "Alice,Company/Finance,u001,\"Analyst,Reviewer\"",
        ].join("\n"),
      ),
    ).toEqual([
      {
        user_name: "Alice",
        org_path: "Company/Finance",
        external_ref: "u001",
        roles: "Analyst,Reviewer",
      },
    ]);
  });

  it("builds normalized import payloads for preview and execute calls", () => {
    expect(
      buildDirectoryImportPayload(
        [
          {
            user_name: "Alice",
            org_path: "Company / Finance",
            external_ref: "u001",
            roles: "Analyst",
          },
        ],
        " / ",
      ),
    ).toEqual({
      rows: [
        {
          user_name: "Alice",
          org_path: "Company / Finance",
          external_ref: "u001",
          roles: "Analyst",
        },
      ],
      delimiter: "/",
    });
  });
});

describe("directory user helpers", () => {
  it("builds create-user payloads with trimmed values and distinct role ids", () => {
    expect(
      buildUserCreatePayload({
        name: " Alice ",
        externalRef: " u001 ",
        orgNodeId: "org_finance",
        roleIds: ["role_analyst", "role_analyst", " role_reviewer "],
      }),
    ).toEqual({
      name: "Alice",
      external_ref: "u001",
      org_node_id: "org_finance",
      role_ids: ["role_analyst", "role_reviewer"],
    });
  });
});
