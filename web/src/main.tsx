import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  ApiOutlined,
  AuditOutlined,
  ClusterOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  EditOutlined,
  ExperimentOutlined,
  EyeOutlined,
  KeyOutlined,
  LockOutlined,
  PlusOutlined,
  SafetyOutlined,
  StopOutlined,
  SyncOutlined,
  TagsOutlined
} from "@ant-design/icons";
import {
  Alert,
  App as AntApp,
  Button,
  ConfigProvider,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Layout,
  Menu,
  Popconfirm,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Tree,
  Typography,
  theme
} from "antd";
import type { ColumnsType } from "antd/es/table";
import enUS from "antd/locale/en_US";
import zhCN from "antd/locale/zh_CN";
import zhTW from "antd/locale/zh_TW";
import "./styles.css";

type PageKey =
  | "overview"
  | "datasources"
  | "tags"
  | "policies"
  | "masking"
  | "apiKeys"
  | "audit"
  | "mcp";

type AnyRecord = Record<string, any>;
type CatalogTreeNode = AnyRecord & {
  key: string;
  type: "datasource" | "resource" | "field";
  children?: CatalogTreeNode[];
};
type Language = "zh-CN" | "zh-TW" | "en-US";
type TranslationParams = Record<string, string | number>;

const translations = {
  "en-US": {
    "brand.controlPlane": "Control Plane",
    "topbar.kicker": "Secure data operations",
    "topbar.apiKey": "API key",
    "topbar.language": "Language",
    "nav.overview": "Overview",
    "nav.datasources": "Data Sources",
    "nav.tags": "Tags",
    "nav.policies": "Policies",
    "nav.masking": "Masking",
    "nav.apiKeys": "API Keys",
    "nav.audit": "Audit Logs",
    "nav.mcp": "MCP Setup",
    "stats.datasources": "Data sources",
    "stats.resources": "Resources",
    "stats.audit": "Audit events",
    "runtime.title": "Runtime pipeline",
    "runtime.description":
      "API key auth, SQL Guard, policy checks, masking, decrypt contexts, and audit events are active in this V1 backend.",
    "common.create": "Create",
    "common.createKey": "Create key",
    "common.save": "Save",
    "common.refresh": "Refresh",
    "common.rows": "{count} rows",
    "common.view": "View",
    "common.edit": "Edit",
    "common.delete": "Delete",
    "common.saved": "Saved",
    "common.deleted": "Deleted",
    "common.revoked": "Revoked",
    "common.detailsTitle": "{title} Details",
    "common.createTitle": "Create {title}",
    "common.editTitle": "Edit {title}",
    "common.deleteConfirm": "Delete {title}?",
    "common.revokeConfirm": "Revoke this key?",
    "common.required": "{label} is required",
    "common.validJson": "{label} must be valid JSON",
    "placeholder.resourceSearch": "Search and select a resource",
    "placeholder.tagSearch": "Search and select a tag",
    "apiKey.newTitle": "New API key",
    "field.name": "Name",
    "field.type": "Type",
    "field.status": "Status",
    "field.config": "Config",
    "field.displayName": "Display name",
    "field.queryLanguage": "Query language",
    "field.category": "Category",
    "field.description": "Description",
    "field.subjectType": "Subject type",
    "field.subject": "Subject",
    "field.effect": "Effect",
    "field.action": "Action",
    "field.resourceId": "Resource",
    "field.field": "Field",
    "field.tagId": "Tag ID",
    "field.priority": "Priority",
    "field.strategy": "Strategy",
    "field.scopes": "Scopes",
    "tab.resource": "Resource",
    "tab.field": "Field",
    "policy.resourcePolicies": "Resource Policies",
    "policy.fieldPolicies": "Field Policies",
    "section.fields": "Fields",
    "datasource.new": "New data source",
    "datasource.test": "Test",
    "datasource.scan": "Sync metadata",
    "datasource.tested": "Connection test passed",
    "datasource.scanned": "Metadata synced",
    "datasource.deleteConfirm": "Delete this data source and scanned metadata?",
    "catalog.search": "Search data sources, databases, tables, or fields",
    "catalog.selectPrompt": "Select a data source, database, table, or field to edit details.",
    "catalog.treeTitle": "Data Sources",
    "catalog.detailsTitle": "Catalog Details",
    "catalog.nodeType": "Node type",
    "catalog.fieldInfo": "Field information",
    "catalog.disabledHint": "Disabled assets are hidden from runtime resource discovery.",
    "catalog.tags": "Tags",
    "catalog.noTags": "No tags assigned",
    "catalog.addTag": "Add tag",
    "mcp.toolUrl": "Tool URL",
    "mcp.apiKeyHeader": "API key header",
    "mcp.tools": "Tools",
    "option.active": "active",
    "option.disabled": "disabled",
    "option.allow": "allow",
    "option.deny": "deny",
    "option.fixed": "fixed",
    "option.partial": "partial",
    "option.hash": "hash",
    "option.reversible": "reversible",
    "option.postgres": "postgres",
    "option.mysql": "mysql",
    "option.doris": "doris",
    "option.database": "database",
    "option.schema": "schema",
    "option.relational_table": "table",
    "option.relational_view": "view",
    "column.id": "ID",
    "column.datasource_id": "Datasource",
    "column.resource_id": "Resource",
    "column.resource_label": "Resource",
    "column.api_key_id": "API key",
    "column.user_id": "User",
    "column.name": "Name",
    "column.type": "Type",
    "column.datasource_kind": "Datasource kind",
    "column.config": "Config",
    "column.status": "Status",
    "column.created_at": "Created at",
    "column.updated_at": "Updated at",
    "column.kind": "Kind",
    "column.path": "Path",
    "column.display_name": "Display name",
    "column.query_language": "Query language",
    "column.scanned_at": "Scanned at",
    "column.category": "Category",
    "column.description": "Description",
    "column.subject_type": "Subject type",
    "column.subject_id": "Subject",
    "column.effect": "Effect",
    "column.action": "Action",
    "column.tag_id": "Tag",
    "column.priority": "Priority",
    "column.field_name": "Field",
    "column.strategy": "Strategy",
    "column.subject": "Subject",
    "column.scopes": "Scopes",
    "column.expires_at": "Expires at",
    "column.event_type": "Event type",
    "column.resource_ids": "Resources",
    "column.query_id": "Query ID",
    "column.data_type": "Data type",
    "column.nullable": "Nullable",
    "column.ordinal_position": "Position",
    "column.metadata": "Metadata"
  },
  "zh-CN": {
    "brand.controlPlane": "控制平面",
    "topbar.kicker": "安全数据操作",
    "topbar.apiKey": "API 密钥",
    "topbar.language": "语言",
    "nav.overview": "概览",
    "nav.datasources": "数据源",
    "nav.tags": "标签",
    "nav.policies": "权限策略",
    "nav.masking": "脱敏",
    "nav.apiKeys": "API 密钥",
    "nav.audit": "审计日志",
    "nav.mcp": "MCP 设置",
    "stats.datasources": "数据源",
    "stats.resources": "资源",
    "stats.audit": "审计事件",
    "runtime.title": "运行时管线",
    "runtime.description": "API 密钥认证、SQL Guard、策略检查、脱敏、解密上下文和审计事件已在 V1 后端启用。",
    "common.create": "新建",
    "common.createKey": "新建密钥",
    "common.save": "保存",
    "common.refresh": "刷新",
    "common.rows": "{count} 行",
    "common.view": "查看",
    "common.edit": "编辑",
    "common.delete": "删除",
    "common.saved": "已保存",
    "common.deleted": "已删除",
    "common.revoked": "已撤销",
    "common.detailsTitle": "{title}详情",
    "common.createTitle": "新建{title}",
    "common.editTitle": "编辑{title}",
    "common.deleteConfirm": "确认删除{title}？",
    "common.revokeConfirm": "确认撤销该密钥？",
    "common.required": "请输入{label}",
    "common.validJson": "{label}必须是有效 JSON",
    "placeholder.resourceSearch": "搜索并选择资源",
    "placeholder.tagSearch": "搜索并选择标签",
    "apiKey.newTitle": "新 API 密钥",
    "field.name": "名称",
    "field.type": "类型",
    "field.status": "状态",
    "field.config": "配置",
    "field.displayName": "显示名称",
    "field.queryLanguage": "查询语言",
    "field.category": "分类",
    "field.description": "描述",
    "field.subjectType": "主体类型",
    "field.subject": "主体",
    "field.effect": "效果",
    "field.action": "操作",
    "field.resourceId": "资源",
    "field.field": "字段",
    "field.tagId": "标签 ID",
    "field.priority": "优先级",
    "field.strategy": "策略",
    "field.scopes": "权限范围",
    "tab.resource": "资源",
    "tab.field": "字段",
    "policy.resourcePolicies": "资源权限策略",
    "policy.fieldPolicies": "字段权限策略",
    "section.fields": "字段",
    "datasource.new": "新建数据源",
    "datasource.test": "测试连接",
    "datasource.scan": "同步元数据",
    "datasource.tested": "连接测试通过",
    "datasource.scanned": "元数据已同步",
    "datasource.deleteConfirm": "确认删除该数据源及其扫描元数据？",
    "catalog.search": "搜索数据源、库、表或字段",
    "catalog.selectPrompt": "选择一个数据源、数据库、数据表或字段来维护详情。",
    "catalog.treeTitle": "数据源",
    "catalog.detailsTitle": "目录详情",
    "catalog.nodeType": "节点类型",
    "catalog.fieldInfo": "字段信息",
    "catalog.disabledHint": "停用的资产不会出现在运行时资源发现结果中。",
    "catalog.tags": "标签",
    "catalog.noTags": "暂未绑定标签",
    "catalog.addTag": "添加标签",
    "mcp.toolUrl": "工具 URL",
    "mcp.apiKeyHeader": "API 密钥请求头",
    "mcp.tools": "工具",
    "option.active": "启用",
    "option.disabled": "停用",
    "option.allow": "允许",
    "option.deny": "拒绝",
    "option.fixed": "固定替换",
    "option.partial": "部分遮罩",
    "option.hash": "哈希",
    "option.reversible": "可逆加密",
    "option.postgres": "Postgres",
    "option.mysql": "MySQL",
    "option.doris": "Doris",
    "option.database": "数据库",
    "option.schema": "Schema",
    "option.relational_table": "数据表",
    "option.relational_view": "视图",
    "column.id": "ID",
    "column.datasource_id": "数据源",
    "column.resource_id": "资源",
    "column.resource_label": "资源",
    "column.api_key_id": "API 密钥",
    "column.user_id": "用户",
    "column.name": "名称",
    "column.type": "类型",
    "column.datasource_kind": "数据源类型",
    "column.config": "配置",
    "column.status": "状态",
    "column.created_at": "创建时间",
    "column.updated_at": "更新时间",
    "column.kind": "类型",
    "column.path": "路径",
    "column.display_name": "显示名称",
    "column.query_language": "查询语言",
    "column.scanned_at": "扫描时间",
    "column.category": "分类",
    "column.description": "描述",
    "column.subject_type": "主体类型",
    "column.subject_id": "主体",
    "column.effect": "效果",
    "column.action": "操作",
    "column.tag_id": "标签",
    "column.priority": "优先级",
    "column.field_name": "字段",
    "column.strategy": "策略",
    "column.subject": "主体",
    "column.scopes": "权限范围",
    "column.expires_at": "过期时间",
    "column.event_type": "事件类型",
    "column.resource_ids": "资源",
    "column.query_id": "查询 ID",
    "column.data_type": "数据类型",
    "column.nullable": "可为空",
    "column.ordinal_position": "位置",
    "column.metadata": "元数据"
  },
  "zh-TW": {
    "brand.controlPlane": "控制平面",
    "topbar.kicker": "安全資料操作",
    "topbar.apiKey": "API 金鑰",
    "topbar.language": "語言",
    "nav.overview": "總覽",
    "nav.datasources": "資料來源",
    "nav.tags": "標籤",
    "nav.policies": "權限策略",
    "nav.masking": "遮罩",
    "nav.apiKeys": "API 金鑰",
    "nav.audit": "稽核日誌",
    "nav.mcp": "MCP 設定",
    "stats.datasources": "資料來源",
    "stats.resources": "資源",
    "stats.audit": "稽核事件",
    "runtime.title": "執行時管線",
    "runtime.description": "API 金鑰驗證、SQL Guard、策略檢查、遮罩、解密上下文與稽核事件已在 V1 後端啟用。",
    "common.create": "新增",
    "common.createKey": "新增金鑰",
    "common.save": "儲存",
    "common.refresh": "重新整理",
    "common.rows": "{count} 筆",
    "common.view": "查看",
    "common.edit": "編輯",
    "common.delete": "刪除",
    "common.saved": "已儲存",
    "common.deleted": "已刪除",
    "common.revoked": "已撤銷",
    "common.detailsTitle": "{title}詳情",
    "common.createTitle": "新增{title}",
    "common.editTitle": "編輯{title}",
    "common.deleteConfirm": "確認刪除{title}？",
    "common.revokeConfirm": "確認撤銷此金鑰？",
    "common.required": "請輸入{label}",
    "common.validJson": "{label}必須是有效 JSON",
    "placeholder.resourceSearch": "搜尋並選擇資源",
    "placeholder.tagSearch": "搜尋並選擇標籤",
    "apiKey.newTitle": "新 API 金鑰",
    "field.name": "名稱",
    "field.type": "類型",
    "field.status": "狀態",
    "field.config": "設定",
    "field.displayName": "顯示名稱",
    "field.queryLanguage": "查詢語言",
    "field.category": "分類",
    "field.description": "描述",
    "field.subjectType": "主體類型",
    "field.subject": "主體",
    "field.effect": "效果",
    "field.action": "操作",
    "field.resourceId": "資源",
    "field.field": "欄位",
    "field.tagId": "標籤 ID",
    "field.priority": "優先順序",
    "field.strategy": "策略",
    "field.scopes": "權限範圍",
    "tab.resource": "資源",
    "tab.field": "欄位",
    "policy.resourcePolicies": "資源權限策略",
    "policy.fieldPolicies": "欄位權限策略",
    "section.fields": "欄位",
    "datasource.new": "新增資料來源",
    "datasource.test": "測試連線",
    "datasource.scan": "同步中繼資料",
    "datasource.tested": "連線測試通過",
    "datasource.scanned": "中繼資料已同步",
    "datasource.deleteConfirm": "確認刪除此資料來源及其掃描中繼資料？",
    "catalog.search": "搜尋資料來源、資料庫、資料表或欄位",
    "catalog.selectPrompt": "選擇一個資料來源、資料庫、資料表或欄位來維護詳情。",
    "catalog.treeTitle": "資料來源",
    "catalog.detailsTitle": "目錄詳情",
    "catalog.nodeType": "節點類型",
    "catalog.fieldInfo": "欄位資訊",
    "catalog.disabledHint": "停用的資產不會出現在執行時資源探索結果中。",
    "catalog.tags": "標籤",
    "catalog.noTags": "尚未綁定標籤",
    "catalog.addTag": "新增標籤",
    "mcp.toolUrl": "工具 URL",
    "mcp.apiKeyHeader": "API 金鑰標頭",
    "mcp.tools": "工具",
    "option.active": "啟用",
    "option.disabled": "停用",
    "option.allow": "允許",
    "option.deny": "拒絕",
    "option.fixed": "固定替換",
    "option.partial": "部分遮罩",
    "option.hash": "雜湊",
    "option.reversible": "可逆加密",
    "option.postgres": "Postgres",
    "option.mysql": "MySQL",
    "option.doris": "Doris",
    "option.database": "資料庫",
    "option.schema": "Schema",
    "option.relational_table": "資料表",
    "option.relational_view": "檢視",
    "column.id": "ID",
    "column.datasource_id": "資料來源",
    "column.resource_id": "資源",
    "column.resource_label": "資源",
    "column.api_key_id": "API 金鑰",
    "column.user_id": "使用者",
    "column.name": "名稱",
    "column.type": "類型",
    "column.datasource_kind": "資料來源類型",
    "column.config": "設定",
    "column.status": "狀態",
    "column.created_at": "建立時間",
    "column.updated_at": "更新時間",
    "column.kind": "類型",
    "column.path": "路徑",
    "column.display_name": "顯示名稱",
    "column.query_language": "查詢語言",
    "column.scanned_at": "掃描時間",
    "column.category": "分類",
    "column.description": "描述",
    "column.subject_type": "主體類型",
    "column.subject_id": "主體",
    "column.effect": "效果",
    "column.action": "操作",
    "column.tag_id": "標籤",
    "column.priority": "優先順序",
    "column.field_name": "欄位",
    "column.strategy": "策略",
    "column.subject": "主體",
    "column.scopes": "權限範圍",
    "column.expires_at": "到期時間",
    "column.event_type": "事件類型",
    "column.resource_ids": "資源",
    "column.query_id": "查詢 ID",
    "column.data_type": "資料類型",
    "column.nullable": "可為空",
    "column.ordinal_position": "位置",
    "column.metadata": "中繼資料"
  }
} as const;

type TranslationKey = keyof (typeof translations)["en-US"];
type I18nContextValue = {
  /** Currently selected console language. */
  language: Language;
  /** Persist and apply a new console language. */
  setLanguage: (language: Language) => void;
  /** Translate a key and interpolate optional named parameters. */
  t: (key: TranslationKey, params?: TranslationParams) => string;
};

const I18nContext = React.createContext<I18nContextValue | null>(null);

type FieldConfig = {
  /** Backend payload field name used by Ant Design forms. */
  name: string;
  label: TranslationKey;
  input?: "text" | "textarea" | "json" | "number" | "tags" | "select" | "resource-select";
  required?: boolean;
  options?: string[];
  resourceOptions?: AnyRecord[];
  loading?: boolean;
};

const languages: Array<{ value: Language; label: string }> = [
  { value: "zh-CN", label: "简体中文" },
  { value: "zh-TW", label: "繁體中文" },
  { value: "en-US", label: "English" }
];

const antdLocales: Record<Language, typeof zhCN> = {
  "zh-CN": zhCN,
  "zh-TW": zhTW,
  "en-US": enUS
};

const pages: Array<{ key: PageKey; labelKey: TranslationKey; icon: React.ReactNode }> = [
  { key: "overview", labelKey: "nav.overview", icon: <ClusterOutlined /> },
  { key: "datasources", labelKey: "nav.datasources", icon: <DatabaseOutlined /> },
  { key: "tags", labelKey: "nav.tags", icon: <TagsOutlined /> },
  { key: "policies", labelKey: "nav.policies", icon: <SafetyOutlined /> },
  { key: "masking", labelKey: "nav.masking", icon: <LockOutlined /> },
  { key: "apiKeys", labelKey: "nav.apiKeys", icon: <KeyOutlined /> },
  { key: "audit", labelKey: "nav.audit", icon: <AuditOutlined /> },
  { key: "mcp", labelKey: "nav.mcp", icon: <ApiOutlined /> }
];

function getStoredLanguage(): Language {
  /** Return the persisted language, falling back to Simplified Chinese. */

  const stored = localStorage.getItem("adg.language");
  return languages.some((item) => item.value === stored) ? (stored as Language) : "zh-CN";
}

function translate(language: Language, key: TranslationKey, params: TranslationParams = {}) {
  /** Resolve a translation key and replace simple `{name}` placeholders. */

  let text: string = translations[language][key] || translations["en-US"][key] || key;
  for (const [name, value] of Object.entries(params)) {
    text = text.split(`{${name}}`).join(String(value));
  }
  return text;
}

function useI18n() {
  /** Read the i18n context and fail loudly if the provider is missing. */

  const context = React.useContext(I18nContext);
  if (!context) {
    throw new Error("I18n context is missing");
  }
  return context;
}

function optionLabel(value: string, t: I18nContextValue["t"]) {
  /** Translate known enum-like values while leaving custom values untouched. */

  const key = `option.${value}` as TranslationKey;
  return key in translations["en-US"] ? t(key) : value;
}

function columnLabel(key: string, t: I18nContextValue["t"]) {
  /** Translate known table column keys while preserving unknown backend fields. */

  const translationKey = `column.${key}` as TranslationKey;
  return translationKey in translations["en-US"] ? t(translationKey) : key;
}

function useApi() {
  /** Keep the API key in local storage and attach it to every console request. */

  const [apiKey, setApiKey] = useState(localStorage.getItem("adg.apiKey") || "adg_admin");
  const saveApiKey = (value: string) => {
    localStorage.setItem("adg.apiKey", value);
    setApiKey(value);
  };
  const request = async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
    // The frontend talks to relative paths so Vite and production hosting can proxy them.
    const response = await fetch(path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-ADG-API-Key": apiKey,
        ...(options.headers || {})
      }
    });
    if (!response.ok) {
      throw new Error((await response.text()) || response.statusText);
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  };
  return { apiKey, saveApiKey, request };
}

function useData<T>(loader: () => Promise<T>, deps: React.DependencyList) {
  /** Load async table/detail data with a reload function and simple error state. */

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reload = () => {
    setLoading(true);
    setError(null);
    loader()
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  };
  useEffect(reload, deps);
  return { data, loading, error, reload };
}

function App() {
  /** Configure Ant Design theming and provide translation state to the console. */

  const [language, setLanguageState] = useState<Language>(getStoredLanguage);
  const setLanguage = (value: Language) => {
    localStorage.setItem("adg.language", value);
    setLanguageState(value);
  };
  const t = (key: TranslationKey, params?: TranslationParams) => translate(language, key, params);
  return (
    <ConfigProvider
      locale={antdLocales[language]}
      button={{ autoInsertSpace: false }}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: "#12766f",
          colorInfo: "#12766f",
          colorSuccess: "#168a5b",
          colorWarning: "#b7791f",
          colorError: "#b42318",
          borderRadius: 6,
          fontFamily: "Segoe UI, ui-sans-serif, system-ui, sans-serif",
          fontSize: 13,
          colorBgLayout: "#eef3f1",
          colorBgContainer: "#ffffff",
          colorText: "#17211f",
          colorTextSecondary: "#61716c",
          colorBorder: "#d7e1de"
        }
      }}
    >
      <AntApp>
        <I18nContext.Provider value={{ language, setLanguage, t }}>
          <ConsoleApp />
        </I18nContext.Provider>
      </AntApp>
    </ConfigProvider>
  );
}

function ConsoleApp() {
  /** Render the fixed shell, navigation, language switcher, and active page. */

  const { language, setLanguage, t } = useI18n();
  const [page, setPage] = useState<PageKey>("overview");
  const api = useApi();
  const navigationItems = pages.map((item) => ({
    key: item.key,
    icon: item.icon,
    label: t(item.labelKey)
  }));
  const currentPageTitle = t(pages.find((item) => item.key === page)?.labelKey || "nav.overview");
  return (
    <Layout className="shell">
      <Layout.Sider width={248} className="sider">
        <div className="brand">
            <span className="brand-mark">ADG</span>
            <span>
              <span className="brand-name">AI Data Access Gateway</span>
              <span className="brand-subtitle">{t("brand.controlPlane")}</span>
            </span>
          </div>
          <Menu
            mode="inline"
            selectedKeys={[page]}
            items={navigationItems}
            onClick={({ key }) => setPage(key as PageKey)}
          />
      </Layout.Sider>
      <Layout>
        <Layout.Header className="topbar">
          <div>
            <Typography.Text className="page-kicker">{t("topbar.kicker")}</Typography.Text>
            <Typography.Title level={3} className="page-title">
              {currentPageTitle}
            </Typography.Title>
          </div>
          <Select
            className="mobile-page-select"
            aria-label={currentPageTitle}
            value={page}
            options={navigationItems.map((item) => ({ key: item.key, value: item.key, label: item.label }))}
            onChange={(key) => setPage(key as PageKey)}
          />
          <div className="topbar-actions">
            <Select
              className="language-select"
              aria-label={t("topbar.language")}
              value={language}
              options={languages}
              onChange={setLanguage}
            />
            <Space.Compact className="key-input">
              <Button>{t("topbar.apiKey")}</Button>
              <Input
                id="adg-api-key"
                name="adg-api-key"
                autoComplete="off"
                value={api.apiKey}
                onChange={(event) => api.saveApiKey(event.target.value)}
              />
            </Space.Compact>
          </div>
        </Layout.Header>
        <Layout.Content className="content">
          <Page page={page} api={api} />
        </Layout.Content>
      </Layout>
    </Layout>
  );
}

function Page({ page, api }: { page: PageKey; api: ReturnType<typeof useApi> }) {
  /** Route the selected navigation key to its console page component. */

  if (page === "overview") return <Overview api={api} />;
  if (page === "datasources") return <Datasources api={api} />;
  if (page === "tags") return <Tags api={api} />;
  if (page === "policies") return <Policies api={api} />;
  if (page === "masking") return <Masking api={api} />;
  if (page === "apiKeys") return <ApiKeys api={api} />;
  if (page === "audit") return <EndpointTable api={api} title="nav.audit" path="/admin/audit-events" />;
  return <McpSetup api={api} />;
}

function Overview({ api }: { api: ReturnType<typeof useApi> }) {
  /** Show a compact operational summary for the current control-plane data. */

  const { t } = useI18n();
  const datasources = useData<AnyRecord[]>(() => api.request("/admin/datasources"), [api.apiKey]);
  const resources = useData<AnyRecord[]>(() => api.request("/admin/resources"), [api.apiKey]);
  const audit = useData<AnyRecord[]>(() => api.request("/admin/audit-events"), [api.apiKey]);
  return (
    <div className="workspace">
      <div className="stats">
        <Statistic title={t("stats.datasources")} value={datasources.data?.length || 0} />
        <Statistic title={t("stats.resources")} value={resources.data?.length || 0} />
        <Statistic title={t("stats.audit")} value={audit.data?.length || 0} />
      </div>
      <Alert
        type="info"
        showIcon
        message={t("runtime.title")}
        description={t("runtime.description")}
        className="runtime-alert"
      />
    </div>
  );
}

function EndpointTable({ api, title, path }: { api: ReturnType<typeof useApi>; title: TranslationKey; path: string }) {
  /** Render read-only endpoint data with row details in a drawer. */

  const { t } = useI18n();
  const state = useData<AnyRecord[]>(() => (path === "__empty__" ? Promise.resolve([]) : api.request(path)), [api.apiKey, path]);
  const [selected, setSelected] = useState<AnyRecord | null>(null);
  const titleText = t(title);
  const columns = columnsFromRows(state.data || [], t);
  return (
    <>
      <DataPanel
        title={titleText}
        state={state}
        columns={columns}
        actions={(row) => <IconAction title={t("common.view")} icon={<EyeOutlined />} onClick={() => setSelected(row)} />}
      />
      <RecordDetails record={selected} title={titleText} onClose={() => setSelected(null)} />
    </>
  );
}

function Datasources({ api }: { api: ReturnType<typeof useApi> }) {
  /** Unified datasource and asset catalog workspace. */

  const { t } = useI18n();
  const datasources = useData<AnyRecord[]>(() => api.request("/admin/datasources"), [api.apiKey]);
  const resources = useData<CatalogTreeNode[]>(() => api.request("/admin/resource-tree"), [api.apiKey]);
  const tags = useData<AnyRecord[]>(() => api.request("/admin/tags"), [api.apiKey]);
  const [search, setSearch] = useState("");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const sourceTree = buildDatasourceTree(datasources.data || [], resources.data || []);
  const treeData = filterCatalogTree(sourceTree, search);
  const flatNodes = flattenCatalogTree(sourceTree);
  const visibleKeys = flattenCatalogTree(treeData).map((node) => node.key);
  const selected = flatNodes.find((node) => node.key === selectedKey) || null;
  const loading = datasources.loading || resources.loading || tags.loading;
  const error = datasources.error || resources.error || tags.error;
  const reloadAll = () => {
    datasources.reload();
    resources.reload();
    tags.reload();
  };

  useEffect(() => {
    if (datasources.data && resources.data) {
      setExpandedKeys(
        flattenCatalogTree(sourceTree)
          .filter((node) => (node.children || []).length > 0)
          .map((node) => node.key)
      );
    }
  }, [datasources.data, resources.data]);

  return (
    <section className="resource-catalog">
      <div className="catalog-tree panel">
        <div className="panel-head">
          <Typography.Title level={4}>{t("catalog.treeTitle")}</Typography.Title>
          <Space>
            <Button icon={<PlusOutlined />} type="primary" onClick={() => setCreateOpen(true)}>
              {t("datasource.new")}
            </Button>
            <Button onClick={reloadAll}>{t("common.refresh")}</Button>
          </Space>
        </div>
        <div className="catalog-tree-body">
          <Input.Search
            allowClear
            className="catalog-search"
            placeholder={t("catalog.search")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          {error ? <Alert type="error" message={error} /> : null}
          <Tree
            blockNode
            className={loading ? "catalog-tree-loading" : undefined}
            showLine
            treeData={toAntTreeData(treeData, t)}
            selectedKeys={selectedKey ? [selectedKey] : []}
            expandedKeys={search ? visibleKeys : expandedKeys}
            onExpand={(keys) => setExpandedKeys(keys)}
            onSelect={(keys) => setSelectedKey(String(keys[0] || ""))}
          />
        </div>
      </div>
      {selected ? (
        <CatalogDetail
          api={api}
          tags={tags.data || []}
          selected={selected}
          onSaved={reloadAll}
          onDeleted={() => {
            setSelectedKey(null);
            reloadAll();
          }}
        />
      ) : (
        <div className="catalog-detail panel">
          <div className="panel-head">
            <Typography.Title level={4}>{t("catalog.detailsTitle")}</Typography.Title>
            <Button type="primary" disabled>{t("common.save")}</Button>
          </div>
          <Empty className="catalog-empty" description={t("catalog.selectPrompt")} />
        </div>
      )}
      <DatasourceCreateDrawer
        api={api}
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={reloadAll}
      />
    </section>
  );
}

function CatalogDetail({
  api,
  tags,
  selected,
  onSaved,
  onDeleted
}: {
  api: ReturnType<typeof useApi>;
  tags: AnyRecord[];
  selected: CatalogTreeNode;
  onSaved: () => void;
  onDeleted: () => void;
}) {
  /** Route the selected catalog node to the correct detail editor. */

  if (selected.type === "datasource") {
    return (
      <DatasourceDetail
        api={api}
        tags={tags}
        selected={selected}
        onSaved={onSaved}
        onDeleted={onDeleted}
      />
    );
  }
  return <AssetDetail api={api} tags={tags} selected={selected} onSaved={onSaved} />;
}

function DatasourceDetail({
  api,
  tags,
  selected,
  onSaved,
  onDeleted
}: {
  api: ReturnType<typeof useApi>;
  tags: AnyRecord[];
  selected: CatalogTreeNode;
  onSaved: () => void;
  onDeleted: () => void;
}) {
  /** Editable datasource form embedded in the catalog detail pane. */

  const { message: messageApi } = AntApp.useApp();
  const { t } = useI18n();
  const [form] = Form.useForm();

  useEffect(() => {
    form.setFieldsValue(toDatasourceFormValues(selected));
  }, [form, selected]);

  const save = async () => {
    const values = await form.validateFields();
    await api.request(`/admin/datasources/${selected.id}`, {
      method: "PATCH",
      body: JSON.stringify(normalizeDatasourceValues(values))
    });
    messageApi.success(t("common.saved"));
    onSaved();
  };
  const test = async () => {
    await api.request(`/admin/datasources/${selected.id}/test`, { method: "POST" });
    messageApi.success(t("datasource.tested"));
  };
  const scan = async () => {
    await api.request(`/admin/datasources/${selected.id}/scan`, { method: "POST" });
    messageApi.success(t("datasource.scanned"));
    onSaved();
  };
  const remove = async () => {
    await api.request(`/admin/datasources/${selected.id}`, { method: "DELETE" });
    messageApi.success(t("common.deleted"));
    onDeleted();
  };

  return (
    <div className="catalog-detail panel">
      <div className="panel-head">
        <Typography.Title level={4}>{t("catalog.detailsTitle")}</Typography.Title>
        <Space>
          <Tag>{optionLabel(String(selected.status || "active"), t)}</Tag>
          <Button icon={<ExperimentOutlined />} onClick={test}>{t("datasource.test")}</Button>
          <Button icon={<SyncOutlined />} onClick={scan}>{t("datasource.scan")}</Button>
          <Popconfirm title={t("datasource.deleteConfirm")} onConfirm={remove}>
            <Button icon={<DeleteOutlined />} />
          </Popconfirm>
          <Button type="primary" onClick={save}>{t("common.save")}</Button>
        </Space>
      </div>
      <div className="catalog-detail-body">
        <Descriptions bordered column={1} size="small">
          <Descriptions.Item label={t("catalog.nodeType")}>
            {t("nav.datasources")}
          </Descriptions.Item>
          <Descriptions.Item label={t("field.type")}>
            {optionLabel(String(selected.datasource_type || selected.type_name || selected.type), t)}
          </Descriptions.Item>
          <Descriptions.Item label={t("column.datasource_kind")}>
            {String(selected.datasource_kind || "")}
          </Descriptions.Item>
        </Descriptions>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={t("field.name")} rules={[{ required: true }]}>
            <Input autoComplete="off" />
          </Form.Item>
          <Form.Item name="status" label={t("field.status")}>
            <Select options={["active", "disabled"].map((value) => ({ value, label: optionLabel(value, t) }))} />
          </Form.Item>
          <Form.Item name="config" label={t("field.config")} rules={[{ required: true }]}>
            <Input.TextArea autoComplete="off" autoSize={{ minRows: 8, maxRows: 16 }} />
          </Form.Item>
        </Form>
        <CatalogTagEditor
          api={api}
          targetType="datasource"
          targetId={selected.id}
          assignedTags={selected.tags || []}
          allTags={tags}
          onChanged={onSaved}
        />
      </div>
    </div>
  );
}

function AssetDetail({
  api,
  tags,
  selected,
  onSaved
}: {
  api: ReturnType<typeof useApi>;
  tags: AnyRecord[];
  selected: CatalogTreeNode;
  onSaved: () => void;
}) {
  /** Editable detail pane for database, table, and field catalog nodes. */

  const { message: messageApi } = AntApp.useApp();
  const { t } = useI18n();
  const [form] = Form.useForm();

  useEffect(() => {
    form.setFieldsValue(toCatalogFormValues(selected));
  }, [form, selected]);

  const save = async () => {
    const values = await form.validateFields();
    const endpoint =
      selected.type === "field"
        ? `/admin/resource-fields/${selected.id}`
        : `/admin/resources/${selected.id}`;
    await api.request(endpoint, {
      method: "PATCH",
      body: JSON.stringify(values)
    });
    messageApi.success(t("common.saved"));
    onSaved();
  };

  return (
    <div className="catalog-detail panel">
      <div className="panel-head">
        <Typography.Title level={4}>{t("catalog.detailsTitle")}</Typography.Title>
        <Space>
          <Tag>{optionLabel(String(selected.status || "active"), t)}</Tag>
          <Button type="primary" onClick={save}>{t("common.save")}</Button>
        </Space>
      </div>
      <div className="catalog-detail-body">
        <Descriptions bordered column={1} size="small">
          <Descriptions.Item label={t("catalog.nodeType")}>
            {selected.type === "field" ? t("tab.field") : optionLabel(String(selected.kind), t)}
          </Descriptions.Item>
          <Descriptions.Item label={t("column.path")}>
            <Typography.Text copyable>{String(selected.path || selected.name)}</Typography.Text>
          </Descriptions.Item>
          {selected.type === "field" ? (
            <Descriptions.Item label={t("catalog.fieldInfo")}>
              {selected.data_type} · {t("column.ordinal_position")} {selected.ordinal_position}
            </Descriptions.Item>
          ) : null}
        </Descriptions>
        <Alert type="info" showIcon message={t("catalog.disabledHint")} />
        <Form form={form} layout="vertical">
          {selected.type === "resource" ? (
            <>
              <Form.Item name="display_name" label={t("field.displayName")}>
                <Input autoComplete="off" />
              </Form.Item>
              <Form.Item name="query_language" label={t("field.queryLanguage")}>
                <Input autoComplete="off" />
              </Form.Item>
            </>
          ) : null}
          <Form.Item name="description" label={t("field.description")}>
            <Input.TextArea autoComplete="off" autoSize={{ minRows: 6, maxRows: 14 }} />
          </Form.Item>
          <Form.Item name="status" label={t("field.status")}>
            <Select options={["active", "disabled"].map((value) => ({ value, label: optionLabel(value, t) }))} />
          </Form.Item>
        </Form>
        {selected.type === "resource" ? (
          <CatalogTagEditor
            api={api}
            targetType="resource"
            targetId={selected.id}
            assignedTags={selected.tags || []}
            allTags={tags}
            onChanged={onSaved}
          />
        ) : null}
      </div>
    </div>
  );
}

function CatalogTagEditor({
  api,
  targetType,
  targetId,
  assignedTags,
  allTags,
  onChanged
}: {
  api: ReturnType<typeof useApi>;
  targetType: "datasource" | "resource";
  targetId: string;
  assignedTags: AnyRecord[];
  allTags: AnyRecord[];
  onChanged: () => void;
}) {
  /** Manage tag bindings for datasource and resource detail panes. */

  const { message: messageApi } = AntApp.useApp();
  const { t } = useI18n();
  const assignedIds = new Set(assignedTags.map((tag) => String(tag.id)));
  const options = allTags
    .filter((tag) => !assignedIds.has(String(tag.id)))
    .map((tag) => ({
      value: String(tag.id),
      label: `${String(tag.name)}${tag.category ? ` · ${String(tag.category)}` : ""}`,
      searchText: `${String(tag.name)} ${String(tag.category || "")} ${String(tag.description || "")}`.toLowerCase()
    }));

  const bindTag = async (tagId: string) => {
    await api.request(targetType === "datasource" ? "/admin/datasource-tags" : "/admin/resource-tags", {
      method: "POST",
      body: JSON.stringify(
        targetType === "datasource"
          ? { tag_id: tagId, datasource_id: targetId }
          : { tag_id: tagId, resource_id: targetId }
      )
    });
    messageApi.success(t("common.saved"));
    onChanged();
  };

  const unbindTag = async (tagId: string) => {
    const search = new URLSearchParams(
      targetType === "datasource"
        ? { tag_id: tagId, datasource_id: targetId }
        : { tag_id: tagId, resource_id: targetId }
    );
    await api.request(`/admin/${targetType}-tags?${search.toString()}`, {
      method: "DELETE"
    });
    messageApi.success(t("common.saved"));
    onChanged();
  };

  return (
    <div className="catalog-tag-editor">
      <Space direction="vertical" size={10} className="full">
        <Typography.Text strong>{t("catalog.tags")}</Typography.Text>
        <Select
          key={`${targetType}:${targetId}:${assignedTags.map((tag) => String(tag.id)).join(",")}`}
          showSearch
          allowClear
          className="catalog-tag-select"
          placeholder={t("placeholder.tagSearch")}
          options={options}
          onSelect={(value) => {
            void bindTag(String(value));
          }}
          filterOption={(input, option) =>
            String((option as { searchText?: string } | undefined)?.searchText || "")
              .includes(input.toLowerCase())
          }
        />
        {assignedTags.length ? (
          <Space wrap size={[8, 8]}>
            {assignedTags.map((tag) => (
              <Tag
                key={String(tag.id)}
                closable
                onClose={(event) => {
                  event.preventDefault();
                  void unbindTag(String(tag.id));
                }}
              >
                {String(tag.name)}
              </Tag>
            ))}
          </Space>
        ) : (
          <Typography.Text type="secondary">{t("catalog.noTags")}</Typography.Text>
        )}
      </Space>
    </div>
  );
}

function DatasourceCreateDrawer({
  api,
  open,
  onClose,
  onCreated
}: {
  api: ReturnType<typeof useApi>;
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  /** Drawer for creating a datasource without leaving the catalog workspace. */

  const { message: messageApi } = AntApp.useApp();
  const { t } = useI18n();
  const [form] = Form.useForm();
  const create = async () => {
    const values = await form.validateFields();
    await api.request("/admin/datasources", {
      method: "POST",
      body: JSON.stringify(normalizeDatasourceValues(values))
    });
    messageApi.success(t("common.saved"));
    onClose();
    onCreated();
  };

  return (
    <Drawer
      title={t("common.createTitle", { title: t("nav.datasources") })}
      open={open}
      onClose={onClose}
      extra={<Button type="primary" onClick={create}>{t("common.save")}</Button>}
      width={520}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          type: "postgres",
          status: "active",
          config: JSON.stringify(
            { host: "localhost", port: 5432, database: "warehouse" },
            null,
            2
          )
        }}
      >
        <Form.Item name="name" label={t("field.name")} rules={[{ required: true }]}>
          <Input autoComplete="off" />
        </Form.Item>
        <Form.Item name="type" label={t("field.type")} rules={[{ required: true }]}>
          <Select options={["postgres", "mysql", "doris"].map((value) => ({ value, label: optionLabel(value, t) }))} />
        </Form.Item>
        <Form.Item name="status" label={t("field.status")} rules={[{ required: true }]}>
          <Select options={["active", "disabled"].map((value) => ({ value, label: optionLabel(value, t) }))} />
        </Form.Item>
        <Form.Item name="config" label={t("field.config")} rules={[{ required: true }]}>
          <Input.TextArea autoComplete="off" autoSize={{ minRows: 8, maxRows: 16 }} />
        </Form.Item>
      </Form>
    </Drawer>
  );
}

function buildDatasourceTree(
  datasources: AnyRecord[],
  resourceRoots: CatalogTreeNode[],
): CatalogTreeNode[] {
  /** Attach scanned assets under their owning datasource root node. */

  return datasources.map((datasource) => ({
    key: `datasource:${datasource.id}`,
    type: "datasource",
    id: datasource.id,
    name: datasource.name,
    display_name: datasource.name,
    datasource_type: datasource.type,
    type_name: datasource.type,
    datasource_kind: datasource.datasource_kind,
    config: datasource.config,
    status: datasource.status,
    tags: datasource.tags || [],
    children: resourceRoots.filter((resource) => resource.datasource_id === datasource.id),
  }));
}

function flattenCatalogTree(nodes: CatalogTreeNode[]): CatalogTreeNode[] {
  /** Flatten the catalog tree for selection lookup and expansion control. */

  return nodes.flatMap((node) => [node, ...flattenCatalogTree(node.children || [])]);
}

function filterCatalogTree(nodes: CatalogTreeNode[], search: string): CatalogTreeNode[] {
  /** Keep matching nodes and ancestors so search still preserves hierarchy. */

  const needle = search.trim().toLowerCase();
  if (!needle) return nodes;
  const filtered: CatalogTreeNode[] = [];
  for (const node of nodes) {
    const children = filterCatalogTree(node.children || [], search);
    const haystack = [
      node.name,
      node.display_name,
      node.path,
      node.kind,
      node.data_type,
      node.description,
      node.datasource_type,
      (node.tags || []).map((tag: AnyRecord) => `${String(tag.name)} ${String(tag.category || "")}`).join(" "),
      JSON.stringify(node.config || {})
    ].join(" ").toLowerCase();
    if (haystack.includes(needle) || children.length) {
      filtered.push({ ...node, children });
    }
  }
  return filtered;
}

function toCatalogFormValues(node: CatalogTreeNode) {
  /** Extract only editable catalog fields from the selected tree node. */

  return node.type === "field"
    ? { description: node.description, status: node.status || "active" }
    : {
        display_name: node.display_name,
        description: node.description,
        query_language: node.query_language,
        status: node.status || "active"
      };
}

function toDatasourceFormValues(node: CatalogTreeNode) {
  /** Convert datasource nodes into form values with pretty JSON config text. */

  return {
    name: node.name,
    status: node.status || "active",
    config: JSON.stringify(node.config || {}, null, 2),
  };
}

function normalizeDatasourceValues(values: AnyRecord) {
  /** Parse datasource config text before sending it to the admin API. */

  return {
    ...values,
    config: typeof values.config === "string" ? JSON.parse(values.config) : values.config,
  };
}

function toAntTreeData(nodes: CatalogTreeNode[], t: I18nContextValue["t"]): AnyRecord[] {
  /** Convert API tree nodes into Ant Design tree data with status-aware labels. */

  return nodes.map((node) => {
    const children = toAntTreeData(node.children || [], t);
    const label = String(node.display_name || node.name);
    const meta = node.type === "datasource" ? String(node.datasource_type || "") : "";
    return {
      key: node.key,
      title: (
        <Space size={6} className="catalog-node-title">
          <span>{label}</span>
          {meta ? <Tag>{optionLabel(meta, t)}</Tag> : null}
          {node.status === "disabled" ? <Tag>{optionLabel("disabled", t)}</Tag> : null}
        </Space>
      ),
      ...(children.length ? { children } : {})
    };
  });
}

function Tags({ api }: { api: ReturnType<typeof useApi> }) {
  /** Governance tag CRUD page. */

  return (
    <CrudPanel
      api={api}
      title="nav.tags"
      listPath="/admin/tags"
      createPath="/admin/tags"
      updatePath={(row) => `/admin/tags/${row.id}`}
      deletePath={(row) => `/admin/tags/${row.id}`}
      fields={[
        { name: "name", label: "field.name", required: true },
        { name: "category", label: "field.category" },
        { name: "description", label: "field.description", input: "textarea" }
      ]}
      initialValues={{}}
    />
  );
}

function Policies({ api }: { api: ReturnType<typeof useApi> }) {
  /** Policy area split into resource-level and field-level tabs. */

  const { t } = useI18n();
  return (
    <Tabs
      items={[
        { key: "resource", label: t("tab.resource"), children: <CrudPolicy api={api} kind="resource" /> },
        { key: "field", label: t("tab.field"), children: <CrudPolicy api={api} kind="field" /> }
      ]}
    />
  );
}

function CrudPolicy({ api, kind }: { api: ReturnType<typeof useApi>; kind: "resource" | "field" }) {
  /** Shared policy CRUD page that adapts required fields by policy kind. */

  const isField = kind === "field";
  const resources = useData<AnyRecord[]>(() => api.request("/admin/resources"), [api.apiKey]);
  return (
    <CrudPanel
      api={api}
      title={isField ? "policy.fieldPolicies" : "policy.resourcePolicies"}
      listPath={`/admin/${kind}-policies`}
      createPath={`/admin/${kind}-policies`}
      updatePath={(row) => `/admin/${kind}-policies/${row.id}`}
      deletePath={(row) => `/admin/${kind}-policies/${row.id}`}
      fields={[
        { name: "subject_type", label: "field.subjectType", required: true },
        { name: "subject_id", label: "field.subject", required: true },
        { name: "effect", label: "field.effect", input: "select", options: ["allow", "deny"], required: true },
        { name: "action", label: "field.action", required: true },
        {
          name: "resource_id",
          label: "field.resourceId",
          input: "resource-select",
          resourceOptions: resources.data || [],
          loading: resources.loading,
          required: isField
        },
        ...(isField ? [{ name: "field_name", label: "field.field" as const, required: true }] : []),
        ...(!isField ? [{ name: "tag_id", label: "field.tagId" as const }] : []),
        { name: "priority", label: "field.priority", input: "number" as const },
        { name: "status", label: "field.status", input: "select" as const, options: ["active", "disabled"] }
      ]}
      initialValues={{ action: "read", effect: "allow", priority: 0, status: "active" }}
    />
  );
}

function Masking({ api }: { api: ReturnType<typeof useApi> }) {
  /** Masking policy CRUD page with searchable resource association. */

  const resources = useData<AnyRecord[]>(() => api.request("/admin/resources"), [api.apiKey]);
  return (
    <CrudPanel
      api={api}
      title="nav.masking"
      listPath="/admin/masking-policies"
      createPath="/admin/masking-policies"
      updatePath={(row) => `/admin/masking-policies/${row.id}`}
      deletePath={(row) => `/admin/masking-policies/${row.id}`}
      fields={[
        {
          name: "resource_id",
          label: "field.resourceId",
          input: "resource-select",
          resourceOptions: resources.data || [],
          loading: resources.loading,
          required: true
        },
        { name: "field_name", label: "field.field", required: true },
        { name: "subject_type", label: "field.subjectType" },
        { name: "subject_id", label: "field.subject" },
        { name: "strategy", label: "field.strategy", input: "select", options: ["fixed", "partial", "hash", "reversible"], required: true },
        { name: "config", label: "field.config", input: "json", required: true },
        { name: "status", label: "field.status", input: "select", options: ["active", "disabled"] }
      ]}
      initialValues={{ strategy: "fixed", config: { replacement: "REDACTED" }, status: "active" }}
    />
  );
}

function ApiKeys({ api }: { api: ReturnType<typeof useApi> }) {
  /** API key management page; raw keys are shown only after creation. */

  const { message: messageApi, modal } = AntApp.useApp();
  const { t } = useI18n();
  const state = useData<AnyRecord[]>(() => api.request("/admin/api-keys"), [api.apiKey]);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<AnyRecord | null>(null);
  const [editing, setEditing] = useState<AnyRecord | null>(null);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();
  const create = async () => {
    const values = await form.validateFields();
    const created = await api.request<AnyRecord>("/admin/api-keys", {
      method: "POST",
      body: JSON.stringify({ name: values.name, scopes: values.scopes })
    });
    modal.info({ title: t("apiKey.newTitle"), content: <Typography.Text copyable>{created.api_key}</Typography.Text> });
    setOpen(false);
    state.reload();
  };
  const edit = async () => {
    if (!editing) return;
    const values = await editForm.validateFields();
    await api.request(`/admin/api-keys/${editing.id}`, {
      method: "PATCH",
      body: JSON.stringify(values)
    });
    messageApi.success(t("common.saved"));
    setEditing(null);
    state.reload();
  };
  const revoke = async (row: AnyRecord) => {
    await api.request(`/admin/api-keys/${row.id}/revoke`, { method: "POST" });
    messageApi.success(t("common.revoked"));
    state.reload();
  };
  return (
    <Space direction="vertical" size={12} className="full">
      <Button type="primary" onClick={() => setOpen(true)}>{t("common.createKey")}</Button>
      <DataPanel
        title={t("nav.apiKeys")}
        state={state}
        columns={columnsFromRows(state.data || [], t)}
        actions={(row) => (
          <Space size={4}>
            <IconAction title={t("common.view")} icon={<EyeOutlined />} onClick={() => setSelected(row)} />
            <IconAction
              title={t("common.edit")}
              icon={<EditOutlined />}
              onClick={() => {
                setEditing(row);
                editForm.setFieldsValue(row);
              }}
            />
            <Popconfirm title={t("common.revokeConfirm")} onConfirm={() => revoke(row)}>
              <Button size="small" icon={<StopOutlined />} />
            </Popconfirm>
          </Space>
        )}
      />
      <RecordDetails record={selected} title={t("nav.apiKeys")} onClose={() => setSelected(null)} />
      <Drawer title={t("common.createTitle", { title: t("nav.apiKeys") })} open={open} onClose={() => setOpen(false)} extra={<Button type="primary" onClick={create}>{t("common.save")}</Button>}>
        <Form form={form} layout="vertical" initialValues={{ scopes: ["runtime"] }}>
          <Form.Item name="name" label={t("field.name")} rules={[{ required: true }]}><Input autoComplete="off" /></Form.Item>
          <Form.Item name="scopes" label={t("field.scopes")}><Select mode="tags" /></Form.Item>
        </Form>
      </Drawer>
      <Drawer title={t("common.editTitle", { title: t("nav.apiKeys") })} open={Boolean(editing)} onClose={() => setEditing(null)} extra={<Button type="primary" onClick={edit}>{t("common.save")}</Button>}>
        <Form form={editForm} layout="vertical">
          <Form.Item name="name" label={t("field.name")} rules={[{ required: true }]}><Input autoComplete="off" /></Form.Item>
          <Form.Item name="scopes" label={t("field.scopes")}><Select mode="tags" /></Form.Item>
        </Form>
      </Drawer>
    </Space>
  );
}

function McpSetup({ api }: { api: ReturnType<typeof useApi> }) {
  /** Display the HTTP facade details needed by MCP-style clients. */

  const { t } = useI18n();
  const state = useData<AnyRecord>(() => api.request("/admin/mcp/setup"), [api.apiKey]);
  if (state.error) return <Alert type="error" message={state.error} />;
  if (!state.data) return <Empty />;
  return (
    <Descriptions bordered column={1} size="small">
      <Descriptions.Item label={t("mcp.toolUrl")}>{state.data.tool_url}</Descriptions.Item>
      <Descriptions.Item label={t("mcp.apiKeyHeader")}>{state.data.api_key_header}</Descriptions.Item>
      <Descriptions.Item label={t("mcp.tools")}>{state.data.tools.map((tool: string) => <Tag key={tool}>{tool}</Tag>)}</Descriptions.Item>
    </Descriptions>
  );
}

function CrudPanel({
  api,
  title,
  listPath,
  createPath,
  updatePath,
  deletePath,
  fields,
  initialValues,
  onRow,
  stateOverride
}: {
  api: ReturnType<typeof useApi>;
  title: TranslationKey;
  listPath: string;
  createPath?: string;
  updatePath?: (row: AnyRecord) => string;
  deletePath?: (row: AnyRecord) => string;
  fields: FieldConfig[];
  initialValues: AnyRecord;
  onRow?: (row: AnyRecord) => React.HTMLAttributes<HTMLElement>;
  stateOverride?: { data: AnyRecord[] | null; loading: boolean; error: string | null; reload: () => void };
}) {
  /** Generic CRUD shell used by most console tables and drawer forms. */

  const { message: messageApi } = AntApp.useApp();
  const { t } = useI18n();
  const titleText = t(title);
  const loadedState = useData<AnyRecord[]>(() => api.request(listPath), [api.apiKey, listPath]);
  const state = stateOverride || loadedState;
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<AnyRecord | null>(null);
  const [editing, setEditing] = useState<AnyRecord | null>(null);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();
  const save = async () => {
    // Create payloads merge defaults with form values before JSON normalization.
    if (!createPath) return;
    const values = await form.validateFields();
    await api.request(createPath, {
      method: "POST",
      body: JSON.stringify(normalizeValues({ ...initialValues, ...values }, fields, t))
    });
    messageApi.success(t("common.saved"));
    setOpen(false);
    state.reload();
  };
  const update = async () => {
    // Update payloads include only the edit drawer values.
    if (!editing || !updatePath) return;
    const values = await editForm.validateFields();
    await api.request(updatePath(editing), {
      method: "PATCH",
      body: JSON.stringify(normalizeValues(values, fields, t))
    });
    messageApi.success(t("common.saved"));
    setEditing(null);
    state.reload();
  };
  const remove = async (row: AnyRecord) => {
    if (!deletePath) return;
    await api.request(deletePath(row), { method: "DELETE" });
    messageApi.success(t("common.deleted"));
    state.reload();
  };
  return (
    <Space direction="vertical" size={12} className="full">
      {createPath ? <Button type="primary" onClick={() => { form.resetFields(); form.setFieldsValue(toFormValues(initialValues, fields)); setOpen(true); }}>{t("common.create")}</Button> : null}
      <DataPanel
        title={titleText}
        state={state}
        columns={columnsFromRows(state.data || [], t)}
        onRow={onRow}
        actions={(row) => (
          <Space size={4} onClick={(event) => event.stopPropagation()}>
            <IconAction title={t("common.view")} icon={<EyeOutlined />} onClick={() => setSelected(row)} />
            {updatePath ? (
              <IconAction
                title={t("common.edit")}
                icon={<EditOutlined />}
                onClick={() => {
                  setEditing(row);
                  editForm.setFieldsValue(toFormValues(row, fields));
                }}
              />
            ) : null}
            {deletePath ? (
              <Popconfirm title={t("common.deleteConfirm", { title: titleText })} onConfirm={() => remove(row)}>
                <Button size="small" icon={<DeleteOutlined />} />
              </Popconfirm>
            ) : null}
          </Space>
        )}
      />
      <RecordDetails record={selected} title={titleText} onClose={() => setSelected(null)} />
      <Drawer title={t("common.createTitle", { title: titleText })} open={open} onClose={() => setOpen(false)} extra={<Button type="primary" onClick={save}>{t("common.save")}</Button>}>
        <Form form={form} layout="vertical" initialValues={toFormValues(initialValues, fields)}>
          {fields.map((field) => renderField(field, t))}
        </Form>
      </Drawer>
      <Drawer title={t("common.editTitle", { title: titleText })} open={Boolean(editing)} onClose={() => setEditing(null)} extra={<Button type="primary" onClick={update}>{t("common.save")}</Button>}>
        <Form form={editForm} layout="vertical">
          {fields.map((field) => renderField(field, t))}
        </Form>
      </Drawer>
    </Space>
  );
}

function DataPanel({
  title,
  state,
  columns,
  actions,
  onRow
}: {
  title: string;
  state: { data: AnyRecord[] | null; loading: boolean; error: string | null; reload: () => void };
  columns: ColumnsType<AnyRecord>;
  actions?: (row: AnyRecord) => React.ReactNode;
  onRow?: (row: AnyRecord) => React.HTMLAttributes<HTMLElement>;
}) {
  /** Shared table panel with optional row actions and a reload control. */

  const { t } = useI18n();
  const count = state.data?.length || 0;
  const tableColumns = actions
    ? [
        ...columns,
        {
          title: "",
          key: "actions",
          fixed: "right" as const,
          width: 112,
          render: (_: unknown, row: AnyRecord) => actions(row)
        }
      ]
    : columns;
  return (
    <section className="panel">
      <div className="panel-head">
        <Typography.Title level={4}>{title}</Typography.Title>
        <Space><Tag>{t("common.rows", { count })}</Tag><Button onClick={state.reload}>{t("common.refresh")}</Button></Space>
      </div>
      {state.error ? <Alert type="error" message={state.error} /> : (
        <Table size="small" rowKey={(row) => row.id || JSON.stringify(row)} loading={state.loading} dataSource={state.data || []} columns={tableColumns} onRow={onRow} pagination={{ pageSize: 8 }} scroll={{ x: true }} />
      )}
    </section>
  );
}

function columnsFromRows(rows: AnyRecord[], t: I18nContextValue["t"]): ColumnsType<AnyRecord> {
  /** Infer table columns from backend rows while hiding technical foreign keys. */

  const hiddenKeys = new Set(["id", "datasource_id", "resource_id", "api_key_id"]);
  const keys = Array.from(new Set(rows.flatMap((row) => Object.keys(row))))
    .filter((key) => !hiddenKeys.has(key))
    .slice(0, 8);
  return keys.map((key) => ({
    title: columnLabel(key, t),
    dataIndex: key,
    ellipsis: true,
    render: (value: unknown) => {
      if (typeof value === "object" && value !== null) {
        return JSON.stringify(value);
      }
      if (typeof value === "string") {
        return optionLabel(value, t);
      }
      return String(value ?? "");
    }
  }));
}

function IconAction({ title, icon, onClick }: { title: string; icon: React.ReactNode; onClick: () => void }) {
  /** Render a compact icon button with an accessible tooltip label. */

  return (
    <Tooltip title={title}>
      <Button size="small" icon={icon} onClick={onClick} />
    </Tooltip>
  );
}

function RecordDetails({
  record,
  title,
  onClose
}: {
  record: AnyRecord | null;
  title: string;
  onClose: () => void;
}) {
  /** Show all fields of a selected row in a copy-friendly details drawer. */

  const { t } = useI18n();
  return (
    <Drawer title={t("common.detailsTitle", { title })} open={Boolean(record)} onClose={onClose} width={560}>
      {record ? (
        <Descriptions bordered column={1} size="small">
          {Object.entries(record).map(([key, value]) => (
            <Descriptions.Item key={key} label={columnLabel(key, t)}>
              <Typography.Text copyable={typeof value === "string"}>
                {typeof value === "object" && value !== null ? JSON.stringify(value) : typeof value === "string" ? optionLabel(value, t) : String(value ?? "")}
              </Typography.Text>
            </Descriptions.Item>
          ))}
        </Descriptions>
      ) : null}
    </Drawer>
  );
}

function ResourceSelect({
  resources,
  loading,
  t,
  value,
  onChange,
  id
}: {
  resources: AnyRecord[];
  loading?: boolean;
  t: I18nContextValue["t"];
  value?: string;
  onChange?: (value?: string) => void;
  id?: string;
}) {
  /** Searchable resource picker used by policy and masking forms. */

  const options = resources.map((resource) => {
    const name = String(resource.display_name || resource.name || resource.id);
    const path = String(resource.path || "");
    const kind = String(resource.kind || "");
    const label = [name, path].filter(Boolean).join(" / ");
    return {
      value: resource.id,
      label,
      searchText: `${name} ${path} ${kind} ${resource.id}`
    };
  });
  return (
    <Select
      id={id}
      value={value}
      onChange={onChange}
      showSearch
      allowClear
      loading={loading}
      className="resource-select"
      placeholder={t("placeholder.resourceSearch")}
      options={options}
      filterOption={(input, option) =>
        String((option as { searchText?: string } | undefined)?.searchText || "")
          .toLowerCase()
          .includes(input.toLowerCase())
      }
    />
  );
}

function renderField(field: FieldConfig, t: I18nContextValue["t"]) {
  /** Convert declarative field config into the matching Ant Design form control. */

  const label = t(field.label);
  const rules = field.required ? [{ required: true, message: t("common.required", { label }) }] : undefined;
  let control: React.ReactNode = <Input autoComplete="off" />;
  if (field.input === "textarea" || field.input === "json") {
    control = <Input.TextArea autoComplete="off" autoSize={{ minRows: 3, maxRows: 8 }} />;
  } else if (field.input === "number") {
    control = <InputNumber className="full" />;
  } else if (field.input === "tags") {
    control = <Select mode="tags" />;
  } else if (field.input === "select") {
    control = <Select options={(field.options || []).map((value) => ({ label: optionLabel(value, t), value }))} />;
  } else if (field.input === "resource-select") {
    control = <ResourceSelect resources={field.resourceOptions || []} loading={field.loading} t={t} />;
  }
  return (
    <Form.Item key={field.name} name={field.name} label={label} rules={rules}>
      {control}
    </Form.Item>
  );
}

function toFormValues(values: AnyRecord, fields: FieldConfig[]) {
  /** Convert API values into form-friendly values, including pretty JSON text. */

  const result = { ...values };
  for (const field of fields) {
    if (field.input === "json" && result[field.name] !== undefined) {
      result[field.name] = JSON.stringify(result[field.name], null, 2);
    }
  }
  return result;
}

function normalizeValues(values: AnyRecord, fields: FieldConfig[], t?: I18nContextValue["t"]) {
  /** Convert form values back into API payloads and validate JSON fields. */

  const result = { ...values };
  for (const field of fields) {
    if (field.input === "json" && typeof result[field.name] === "string") {
      try {
        result[field.name] = JSON.parse(result[field.name]);
      } catch (error) {
        const label = t ? t(field.label) : field.name;
        throw new Error(t ? t("common.validJson", { label }) : `${label} must be valid JSON`);
      }
    }
  }
  return result;
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(<App />);
