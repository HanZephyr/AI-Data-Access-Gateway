export type Language = "zh-CN" | "zh-TW" | "en-US";

export const languageOptions: Array<{ value: Language; label: string }> = [
  { value: "zh-CN", label: "简体中文" },
  { value: "zh-TW", label: "繁體中文" },
  { value: "en-US", label: "English" },
];

const browserLanguageMap: Record<string, Language> = {
  "zh-cn": "zh-CN",
  "zh-tw": "zh-TW",
  "en": "en-US",
  "en-us": "en-US",
  "en-gb": "en-US",
  "en-ca": "en-US",
  "en-au": "en-US",
};

export function resolveInitialLanguage(
  stored: string | null,
  browserLanguages: readonly string[],
): Language {
  if (isSupportedLanguage(stored)) {
    return stored;
  }

  for (const candidate of browserLanguages) {
    const resolved = browserLanguageMap[String(candidate || "").trim().toLowerCase()];
    if (resolved) {
      return resolved;
    }
  }

  return "en-US";
}

function isSupportedLanguage(value: string | null): value is Language {
  return languageOptions.some((option) => option.value === value);
}
