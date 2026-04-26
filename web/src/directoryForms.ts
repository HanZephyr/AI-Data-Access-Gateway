import readXlsxFile from "read-excel-file";

type LooseRecord = Record<string, unknown>;

export type DirectoryImportRow = {
  user_name: string;
  org_path: string;
  external_ref: string;
  roles: string;
};

export type DirectoryUserFormInput = {
  name: unknown;
  externalRef: unknown;
  orgNodeId?: unknown;
  roleIds?: unknown;
};

export type DirectoryImporterPlatform = "feishu" | "wecom" | "dingtalk";

export type DirectoryImportFieldDoc = {
  field: DirectoryImportRow extends infer T ? keyof T & string : string;
  required: boolean;
};

export const directoryImportTemplateFields: DirectoryImportFieldDoc[] = [
  {
    field: "user_name",
    required: true,
  },
  {
    field: "org_path",
    required: false,
  },
  {
    field: "external_ref",
    required: true,
  },
  {
    field: "roles",
    required: false,
  },
];

export function normalizeOrgPathDelimiter(value: unknown) {
  const normalized = typeof value === "string" ? value.trim() : "";
  return normalized || "/";
}

export function buildDirectoryImportPayload(rows: DirectoryImportRow[], delimiter: unknown) {
  return {
    rows: rows.map((row) => ({
      user_name: String(row.user_name || "").trim(),
      org_path: String(row.org_path || "").trim(),
      external_ref: String(row.external_ref || "").trim(),
      roles: String(row.roles || "").trim(),
    })),
    delimiter: normalizeOrgPathDelimiter(delimiter),
  };
}

export function buildDirectoryImporterConfig(
  platform: DirectoryImporterPlatform,
  input: Record<string, unknown>,
) {
  const delimiter = normalizeOrgPathDelimiter(input.delimiter);

  if (platform === "feishu") {
    return {
      delimiter,
      app_id: normalizedText(input.feishuAppId),
      app_secret: normalizedText(input.feishuAppSecret),
      root_department_id: normalizedText(input.feishuRootDepartmentId) || "0",
    };
  }

  if (platform === "wecom") {
    return {
      delimiter,
      corp_id: normalizedText(input.wecomCorpId),
      corp_secret: normalizedText(input.wecomCorpSecret),
      root_department_id: normalizedText(input.wecomRootDepartmentId) || "1",
    };
  }

  return {
    delimiter,
    app_key: normalizedText(input.dingtalkAppKey),
    app_secret: normalizedText(input.dingtalkAppSecret),
    root_department_id: normalizedText(input.dingtalkRootDepartmentId) || "1",
  };
}

export function buildUserCreatePayload(input: DirectoryUserFormInput) {
  const roleCandidates = Array.isArray(input.roleIds) ? input.roleIds : [];
  const role_ids = Array.from(
    new Set(
      roleCandidates
        .map((roleId) => String(roleId || "").trim())
        .filter(Boolean),
    ),
  );

  return {
    name: String(input.name || "").trim(),
    external_ref: String(input.externalRef || "").trim(),
    org_node_id: typeof input.orgNodeId === "string" && input.orgNodeId.trim()
      ? input.orgNodeId.trim()
      : null,
    role_ids,
  };
}

export function parseDirectoryRowsFromText(text: string) {
  const trimmed = text.trim();
  if (!trimmed) return [];

  if (trimmed.startsWith("[") || trimmed.startsWith("{")) {
    return parseDirectoryJson(trimmed);
  }

  return parseDirectoryDelimited(trimmed);
}

export async function parseDirectoryRowsFromFile(file: File) {
  const lowerName = file.name.toLowerCase();
  if (lowerName.endsWith(".xlsx") || lowerName.endsWith(".xls")) {
    const workbookRows = await readXlsxFile(file);
    const [headerRow, ...dataRows] = workbookRows;
    const headers = Array.isArray(headerRow)
      ? headerRow.map((cell) => String(cell ?? "").trim())
      : [];
    const rows = dataRows
      .filter((row) => Array.isArray(row))
      .map((row) =>
        Object.fromEntries(headers.map((header, index) => [header, row[index] ?? ""])),
      );
    return rows.map((row) => ({
      user_name: String(row.user_name || "").trim(),
      org_path: String(row.org_path || "").trim(),
      external_ref: String(row.external_ref || "").trim(),
      roles: normalizeRoleCell(row.roles),
    }));
  }

  return parseDirectoryRowsFromText(await file.text());
}

function parseDirectoryJson(text: string) {
  const parsed = JSON.parse(text) as unknown;
  const rows = Array.isArray(parsed)
    ? parsed
    : parsed && typeof parsed === "object" && Array.isArray((parsed as LooseRecord).rows)
      ? (parsed as { rows: unknown[] }).rows
      : [];

  return rows
    .filter((row): row is LooseRecord => Boolean(row) && typeof row === "object")
    .map((row) => ({
      user_name: String(row.user_name || "").trim(),
      org_path: String(row.org_path || "").trim(),
      external_ref: String(row.external_ref || "").trim(),
      roles: normalizeRoleCell(row.roles),
    }))
    .filter((row) => row.user_name && row.external_ref);
}

function parseDirectoryDelimited(text: string) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) return [];

  const separator = lines[0].includes("\t") ? "\t" : ",";
  const headers = splitDelimitedLine(lines[0], separator);

  return lines.slice(1).map((line) => {
    const values = splitDelimitedLine(line, separator);
    const row = Object.fromEntries(headers.map((header, index) => [header, values[index] || ""]));
    return {
      user_name: String(row.user_name || "").trim(),
      org_path: String(row.org_path || "").trim(),
      external_ref: String(row.external_ref || "").trim(),
      roles: normalizeRoleCell(row.roles),
    };
  });
}

function splitDelimitedLine(line: string, separator: string) {
  const cells: string[] = [];
  let current = "";
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      const next = line[index + 1];
      if (quoted && next === '"') {
        current += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
      continue;
    }
    if (char === separator && !quoted) {
      cells.push(current.trim());
      current = "";
      continue;
    }
    current += char;
  }
  cells.push(current.trim());
  return cells;
}

function normalizeRoleCell(value: unknown) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item || "").trim()).filter(Boolean).join(",");
  }
  return String(value || "").trim();
}

function normalizedText(value: unknown) {
  const normalized = String(value || "").trim();
  return normalized || null;
}
