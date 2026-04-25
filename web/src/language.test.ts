import { describe, expect, it } from "vitest";

import { resolveInitialLanguage } from "./language";

describe("resolveInitialLanguage", () => {
  it("prefers a supported stored language", () => {
    expect(resolveInitialLanguage("zh-TW", ["fr-FR"])).toBe("zh-TW");
  });

  it("falls back to the supported browser language when no stored value exists", () => {
    expect(resolveInitialLanguage(null, ["en"])).toBe("en-US");
    expect(resolveInitialLanguage(null, ["zh-CN"])).toBe("zh-CN");
  });

  it("falls back to English when the browser language is unsupported", () => {
    expect(resolveInitialLanguage(null, ["fr-FR", "ja-JP"])).toBe("en-US");
    expect(resolveInitialLanguage(null, ["zh-HK"])).toBe("en-US");
  });
});
