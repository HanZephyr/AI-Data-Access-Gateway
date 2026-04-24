import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  ApiOutlined,
  AuditOutlined,
  ClusterOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  KeyOutlined,
  LockOutlined,
  SafetyOutlined,
  StopOutlined,
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
  | "resources"
  | "tags"
  | "policies"
  | "masking"
  | "apiKeys"
  | "audit"
  | "mcp";

type AnyRecord = Record<string, any>;
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
    "nav.resources": "Resources",
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
    "apiKey.newTitle": "New API key",
    "field.tenantId": "Tenant ID",
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
    "field.resourceId": "Resource ID",
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
    "column.id": "ID",
    "column.tenant_id": "Tenant",
    "column.datasource_id": "Datasource",
    "column.resource_id": "Resource",
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
    "nav.resources": "资源",
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
    "apiKey.newTitle": "新 API 密钥",
    "field.tenantId": "租户 ID",
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
    "field.resourceId": "资源 ID",
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
    "column.id": "ID",
    "column.tenant_id": "租户",
    "column.datasource_id": "数据源",
    "column.resource_id": "资源",
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
    "nav.resources": "資源",
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
    "apiKey.newTitle": "新 API 金鑰",
    "field.tenantId": "租戶 ID",
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
    "field.resourceId": "資源 ID",
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
    "column.id": "ID",
    "column.tenant_id": "租戶",
    "column.datasource_id": "資料來源",
    "column.resource_id": "資源",
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
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey, params?: TranslationParams) => string;
};

const I18nContext = React.createContext<I18nContextValue | null>(null);

type FieldConfig = {
  name: string;
  label: TranslationKey;
  input?: "text" | "textarea" | "json" | "number" | "tags" | "select";
  required?: boolean;
  options?: string[];
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
  { key: "resources", labelKey: "nav.resources", icon: <ClusterOutlined /> },
  { key: "tags", labelKey: "nav.tags", icon: <TagsOutlined /> },
  { key: "policies", labelKey: "nav.policies", icon: <SafetyOutlined /> },
  { key: "masking", labelKey: "nav.masking", icon: <LockOutlined /> },
  { key: "apiKeys", labelKey: "nav.apiKeys", icon: <KeyOutlined /> },
  { key: "audit", labelKey: "nav.audit", icon: <AuditOutlined /> },
  { key: "mcp", labelKey: "nav.mcp", icon: <ApiOutlined /> }
];

const tenantId = "tenant-a";

function getStoredLanguage(): Language {
  const stored = localStorage.getItem("adg.language");
  return languages.some((item) => item.value === stored) ? (stored as Language) : "zh-CN";
}

function translate(language: Language, key: TranslationKey, params: TranslationParams = {}) {
  let text: string = translations[language][key] || translations["en-US"][key] || key;
  for (const [name, value] of Object.entries(params)) {
    text = text.split(`{${name}}`).join(String(value));
  }
  return text;
}

function useI18n() {
  const context = React.useContext(I18nContext);
  if (!context) {
    throw new Error("I18n context is missing");
  }
  return context;
}

function optionLabel(value: string, t: I18nContextValue["t"]) {
  const key = `option.${value}` as TranslationKey;
  return key in translations["en-US"] ? t(key) : value;
}

function columnLabel(key: string, t: I18nContextValue["t"]) {
  const translationKey = `column.${key}` as TranslationKey;
  return translationKey in translations["en-US"] ? t(translationKey) : key;
}

function useApi() {
  const [apiKey, setApiKey] = useState(localStorage.getItem("adg.apiKey") || "adg_admin");
  const saveApiKey = (value: string) => {
    localStorage.setItem("adg.apiKey", value);
    setApiKey(value);
  };
  const request = async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
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
          <Space className="topbar-actions" size={12} align="center">
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
          </Space>
        </Layout.Header>
        <Layout.Content className="content">
          <Page page={page} api={api} />
        </Layout.Content>
      </Layout>
    </Layout>
  );
}

function Page({ page, api }: { page: PageKey; api: ReturnType<typeof useApi> }) {
  if (page === "overview") return <Overview api={api} />;
  if (page === "datasources") return <Datasources api={api} />;
  if (page === "resources") return <Resources api={api} />;
  if (page === "tags") return <Tags api={api} />;
  if (page === "policies") return <Policies api={api} />;
  if (page === "masking") return <Masking api={api} />;
  if (page === "apiKeys") return <ApiKeys api={api} />;
  if (page === "audit") return <EndpointTable api={api} title="nav.audit" path={`/admin/audit-events?tenant_id=${tenantId}`} />;
  return <McpSetup api={api} />;
}

function Overview({ api }: { api: ReturnType<typeof useApi> }) {
  const { t } = useI18n();
  const datasources = useData<AnyRecord[]>(() => api.request("/admin/datasources"), [api.apiKey]);
  const resources = useData<AnyRecord[]>(() => api.request(`/admin/resources?tenant_id=${tenantId}`), [api.apiKey]);
  const audit = useData<AnyRecord[]>(() => api.request(`/admin/audit-events?tenant_id=${tenantId}`), [api.apiKey]);
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
  return (
    <CrudPanel
      api={api}
      title="nav.datasources"
      listPath="/admin/datasources"
      createPath="/admin/datasources"
      updatePath={(row) => `/admin/datasources/${row.id}`}
      deletePath={(row) => `/admin/datasources/${row.id}`}
      fields={[
        { name: "tenant_id", label: "field.tenantId", required: true },
        { name: "name", label: "field.name", required: true },
        { name: "type", label: "field.type", input: "select", options: ["postgres", "mysql", "doris"], required: true },
        { name: "status", label: "field.status", input: "select", options: ["active", "disabled"], required: true },
        { name: "config", label: "field.config", input: "json", required: true }
      ]}
      initialValues={{
        tenant_id: tenantId,
        type: "postgres",
        status: "active",
        config: { host: "localhost", port: 5432, database: "warehouse" }
      }}
    />
  );
}

function Resources({ api }: { api: ReturnType<typeof useApi> }) {
  const state = useData<AnyRecord[]>(() => api.request(`/admin/resources?tenant_id=${tenantId}`), [api.apiKey]);
  const [resourceId, setResourceId] = useState<string | null>(null);
  const fields = useData<AnyRecord[]>(
    () => (resourceId ? api.request(`/admin/resources/${resourceId}/fields`) : Promise.resolve([])),
    [api.apiKey, resourceId]
  );
  return (
    <Space direction="vertical" size={16} className="full">
      <CrudPanel
        api={api}
        title="nav.resources"
        listPath={`/admin/resources?tenant_id=${tenantId}`}
        updatePath={(row) => `/admin/resources/${row.id}`}
        deletePath={(row) => `/admin/resources/${row.id}`}
        fields={[
          { name: "display_name", label: "field.displayName" },
          { name: "query_language", label: "field.queryLanguage" }
        ]}
        initialValues={{}}
        onRow={(row) => ({ onClick: () => setResourceId(row.id) })}
        stateOverride={state}
      />
      <EndpointTable api={api} title="section.fields" path={resourceId ? `/admin/resources/${resourceId}/fields` : "__empty__"} />
    </Space>
  );
}

function Tags({ api }: { api: ReturnType<typeof useApi> }) {
  return (
    <CrudPanel
      api={api}
      title="nav.tags"
      listPath={`/admin/tags?tenant_id=${tenantId}`}
      createPath="/admin/tags"
      updatePath={(row) => `/admin/tags/${row.id}`}
      deletePath={(row) => `/admin/tags/${row.id}`}
      fields={[
        { name: "name", label: "field.name", required: true },
        { name: "category", label: "field.category" },
        { name: "description", label: "field.description", input: "textarea" }
      ]}
      initialValues={{ tenant_id: tenantId }}
    />
  );
}

function Policies({ api }: { api: ReturnType<typeof useApi> }) {
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
  const isField = kind === "field";
  return (
    <CrudPanel
      api={api}
      title={isField ? "policy.fieldPolicies" : "policy.resourcePolicies"}
      listPath={`/admin/${kind}-policies?tenant_id=${tenantId}`}
      createPath={`/admin/${kind}-policies`}
      updatePath={(row) => `/admin/${kind}-policies/${row.id}`}
      deletePath={(row) => `/admin/${kind}-policies/${row.id}`}
      fields={[
        { name: "subject_type", label: "field.subjectType", required: true },
        { name: "subject_id", label: "field.subject", required: true },
        { name: "effect", label: "field.effect", input: "select", options: ["allow", "deny"], required: true },
        { name: "action", label: "field.action", required: true },
        { name: "resource_id", label: "field.resourceId" },
        ...(isField ? [{ name: "field_name", label: "field.field" as const, required: true }] : []),
        ...(!isField ? [{ name: "tag_id", label: "field.tagId" as const }] : []),
        { name: "priority", label: "field.priority", input: "number" as const },
        { name: "status", label: "field.status", input: "select" as const, options: ["active", "disabled"] }
      ]}
      initialValues={{ tenant_id: tenantId, action: "read", effect: "allow", priority: 0, status: "active" }}
    />
  );
}

function Masking({ api }: { api: ReturnType<typeof useApi> }) {
  return (
    <CrudPanel
      api={api}
      title="nav.masking"
      listPath={`/admin/masking-policies?tenant_id=${tenantId}`}
      createPath="/admin/masking-policies"
      updatePath={(row) => `/admin/masking-policies/${row.id}`}
      deletePath={(row) => `/admin/masking-policies/${row.id}`}
      fields={[
        { name: "resource_id", label: "field.resourceId", required: true },
        { name: "field_name", label: "field.field", required: true },
        { name: "subject_type", label: "field.subjectType" },
        { name: "subject_id", label: "field.subject" },
        { name: "strategy", label: "field.strategy", input: "select", options: ["fixed", "partial", "hash", "reversible"], required: true },
        { name: "config", label: "field.config", input: "json", required: true },
        { name: "status", label: "field.status", input: "select", options: ["active", "disabled"] }
      ]}
      initialValues={{ tenant_id: tenantId, strategy: "fixed", config: { replacement: "REDACTED" }, status: "active" }}
    />
  );
}

function ApiKeys({ api }: { api: ReturnType<typeof useApi> }) {
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
  const keys = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 8);
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

function renderField(field: FieldConfig, t: I18nContextValue["t"]) {
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
  }
  return (
    <Form.Item key={field.name} name={field.name} label={label} rules={rules}>
      {control}
    </Form.Item>
  );
}

function toFormValues(values: AnyRecord, fields: FieldConfig[]) {
  const result = { ...values };
  for (const field of fields) {
    if (field.input === "json" && result[field.name] !== undefined) {
      result[field.name] = JSON.stringify(result[field.name], null, 2);
    }
  }
  return result;
}

function normalizeValues(values: AnyRecord, fields: FieldConfig[], t?: I18nContextValue["t"]) {
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
