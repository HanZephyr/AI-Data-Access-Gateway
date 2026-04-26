type LooseRecord = Record<string, unknown>;
export const SECRET_PLACEHOLDER_BULLETS = "••••••••";

function isSecretPlaceholder(value: unknown) {
  /** Detect redacted secret envelopes returned by the admin datasource API. */

  return Boolean(
    value
      && typeof value === "object"
      && (value as LooseRecord).kind === "secret_placeholder"
      && (value as LooseRecord).configured === true,
  );
}

function readString(value: unknown) {
  /** Normalize string-like values while trimming accidental whitespace. */

  return typeof value === "string" ? value.trim() : "";
}

function readNumber(value: unknown) {
  /** Convert numeric form values into finite numbers when possible. */

  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function normalizePasswordValue(value: unknown) {
  /** Treat placeholder bullets and placeholder objects as unchanged secrets. */

  if (isSecretPlaceholder(value)) {
    return "";
  }
  const normalized = readString(value);
  return normalized === SECRET_PLACEHOLDER_BULLETS ? "" : normalized;
}

export function datasourceFormValuesFromConfig(config: LooseRecord | null | undefined) {
  /** Map persisted datasource config into explicit connection form fields. */

  const source = config || {};
  return {
    host: readString(source.host),
    port: readNumber(source.port),
    database: readString(source.database),
    username: readString(source.username),
    password: normalizePasswordValue(source.password),
  };
}

export function datasourceConfigFromFormValues(values: LooseRecord | null | undefined) {
  /** Collapse datasource form values into the compact API config payload. */

  const source = values || {};
  const config: LooseRecord = {};
  const host = readString(source.host);
  const port = readNumber(source.port);
  const database = readString(source.database);
  const username = readString(source.username);
  const password = normalizePasswordValue(source.password);
  if (host) config.host = host;
  if (port !== undefined) config.port = port;
  if (database) config.database = database;
  if (username) config.username = username;
  if (password) config.password = password;
  return config;
}

export function datasourceHasConfiguredPassword(config: LooseRecord | null | undefined) {
  /** Report whether the datasource already has a stored password hidden behind a placeholder. */

  const source = config || {};
  return isSecretPlaceholder(source.password);
}

export function maskingFormValuesFromConfig(strategy: string, config: LooseRecord | null | undefined) {
  /** Project masking config into form fields based on the selected strategy. */

  const source = config || {};
  if (strategy === "partial") {
    return {
      prefix: readNumber(source.prefix) ?? 2,
      suffix: readNumber(source.suffix) ?? 2,
      fill: readString(source.fill).slice(0, 1) || "*",
    };
  }
  if (strategy === "fixed") {
    return {
      replacement: readString(source.replacement) || "REDACTED",
    };
  }
  return {};
}

export function maskingConfigFromFormValues(strategy: string, values: LooseRecord | null | undefined) {
  /** Build masking config payloads from strategy-specific form fields. */

  const source = values || {};
  if (strategy === "partial") {
    return {
      prefix: readNumber(source.prefix) ?? 2,
      suffix: readNumber(source.suffix) ?? 2,
      fill: readString(source.fill).slice(0, 1) || "*",
    };
  }
  if (strategy === "fixed") {
    return {
      replacement: readString(source.replacement) || "REDACTED",
    };
  }
  return {};
}
