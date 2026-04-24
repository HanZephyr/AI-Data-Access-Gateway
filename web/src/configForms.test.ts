import { describe, expect, it } from "vitest";

import {
  datasourceConfigFromFormValues,
  datasourceFormValuesFromConfig,
  maskingConfigFromFormValues,
  maskingFormValuesFromConfig,
} from "./configForms";

describe("datasource config helpers", () => {
  it("maps datasource config objects into explicit connection fields", () => {
    expect(
      datasourceFormValuesFromConfig({
        host: "db.internal",
        port: 15432,
        database: "warehouse",
        username: "analyst",
        password: "secret",
      }),
    ).toEqual({
      host: "db.internal",
      port: 15432,
      database: "warehouse",
      username: "analyst",
      password: "secret",
    });
  });

  it("normalizes datasource form values into compact config payloads", () => {
    expect(
      datasourceConfigFromFormValues({
        host: "db.internal",
        port: 15432,
        database: "warehouse",
        username: "analyst",
        password: "",
      }),
    ).toEqual({
      host: "db.internal",
      port: 15432,
      database: "warehouse",
      username: "analyst",
    });
  });
});

describe("masking config helpers", () => {
  it("projects fixed masking config into dedicated form fields", () => {
    expect(maskingFormValuesFromConfig("fixed", { replacement: "REDACTED" })).toEqual({
      replacement: "REDACTED",
    });
  });

  it("projects partial masking config into numeric and fill controls", () => {
    expect(maskingFormValuesFromConfig("partial", { prefix: 3, suffix: 2, fill: "#" })).toEqual({
      prefix: 3,
      suffix: 2,
      fill: "#",
    });
  });

  it("returns an empty config for strategies that do not need options", () => {
    expect(maskingConfigFromFormValues("hash", { replacement: "ignored" })).toEqual({});
    expect(maskingConfigFromFormValues("reversible", { prefix: 2, suffix: 2, fill: "*" })).toEqual({});
  });

  it("builds the correct API config for partial masking", () => {
    expect(
      maskingConfigFromFormValues("partial", { prefix: 4, suffix: 1, fill: "#" }),
    ).toEqual({
      prefix: 4,
      suffix: 1,
      fill: "#",
    });
  });
});
