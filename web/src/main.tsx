import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  ApiOutlined,
  AuditOutlined,
  ClusterOutlined,
  DatabaseOutlined,
  KeyOutlined,
  LockOutlined,
  SafetyOutlined,
  TagsOutlined
} from "@ant-design/icons";
import {
  Alert,
  Button,
  ConfigProvider,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Layout,
  Menu,
  Modal,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
  theme
} from "antd";
import type { ColumnsType } from "antd/es/table";
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

const pages: Array<{ key: PageKey; label: string; icon: React.ReactNode }> = [
  { key: "overview", label: "Overview", icon: <ClusterOutlined /> },
  { key: "datasources", label: "Data Sources", icon: <DatabaseOutlined /> },
  { key: "resources", label: "Resources", icon: <ClusterOutlined /> },
  { key: "tags", label: "Tags", icon: <TagsOutlined /> },
  { key: "policies", label: "Policies", icon: <SafetyOutlined /> },
  { key: "masking", label: "Masking", icon: <LockOutlined /> },
  { key: "apiKeys", label: "API Keys", icon: <KeyOutlined /> },
  { key: "audit", label: "Audit Logs", icon: <AuditOutlined /> },
  { key: "mcp", label: "MCP Setup", icon: <ApiOutlined /> }
];

const tenantId = "tenant-a";

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
  const [page, setPage] = useState<PageKey>("overview");
  const api = useApi();
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: "#0f766e",
          borderRadius: 6,
          fontFamily: "ui-sans-serif, Segoe UI, sans-serif"
        }
      }}
    >
      <Layout className="shell">
        <Layout.Sider width={248} className="sider">
          <div className="brand">AI Data Access Gateway</div>
          <Menu
            mode="inline"
            selectedKeys={[page]}
            items={pages}
            onClick={({ key }) => setPage(key as PageKey)}
          />
        </Layout.Sider>
        <Layout>
          <Layout.Header className="topbar">
            <Typography.Text strong>{pages.find((item) => item.key === page)?.label}</Typography.Text>
            <Space.Compact className="key-input">
              <Button>API key</Button>
              <Input
                id="adg-api-key"
                name="adg-api-key"
                value={api.apiKey}
                onChange={(event) => api.saveApiKey(event.target.value)}
              />
            </Space.Compact>
          </Layout.Header>
          <Layout.Content className="content">
            <Page page={page} api={api} />
          </Layout.Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}

function Page({ page, api }: { page: PageKey; api: ReturnType<typeof useApi> }) {
  if (page === "overview") return <Overview api={api} />;
  if (page === "datasources") return <EndpointTable api={api} title="Data Sources" path="/admin/datasources" />;
  if (page === "resources") return <Resources api={api} />;
  if (page === "tags") return <Tags api={api} />;
  if (page === "policies") return <Policies api={api} />;
  if (page === "masking") return <Masking api={api} />;
  if (page === "apiKeys") return <ApiKeys api={api} />;
  if (page === "audit") return <EndpointTable api={api} title="Audit Logs" path={`/admin/audit-events?tenant_id=${tenantId}`} />;
  return <McpSetup api={api} />;
}

function Overview({ api }: { api: ReturnType<typeof useApi> }) {
  const datasources = useData<AnyRecord[]>(() => api.request("/admin/datasources"), [api.apiKey]);
  const resources = useData<AnyRecord[]>(() => api.request(`/admin/resources?tenant_id=${tenantId}`), [api.apiKey]);
  const audit = useData<AnyRecord[]>(() => api.request(`/admin/audit-events?tenant_id=${tenantId}`), [api.apiKey]);
  return (
    <div className="workspace">
      <div className="stats">
        <Statistic title="Data sources" value={datasources.data?.length || 0} />
        <Statistic title="Resources" value={resources.data?.length || 0} />
        <Statistic title="Audit events" value={audit.data?.length || 0} />
      </div>
      <Alert
        type="info"
        showIcon
        message="Runtime pipeline"
        description="API key auth, SQL Guard, policy checks, masking, decrypt contexts, and audit events are active in this V1 backend."
      />
    </div>
  );
}

function EndpointTable({ api, title, path }: { api: ReturnType<typeof useApi>; title: string; path: string }) {
  const state = useData<AnyRecord[]>(() => api.request(path), [api.apiKey, path]);
  const columns = columnsFromRows(state.data || []);
  return <DataPanel title={title} state={state} columns={columns} />;
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
      <DataPanel title="Resources" state={state} columns={columnsFromRows(state.data || [])} onRow={(row) => ({ onClick: () => setResourceId(row.id) })} />
      <DataPanel title="Fields" state={fields} columns={columnsFromRows(fields.data || [])} />
    </Space>
  );
}

function Tags({ api }: { api: ReturnType<typeof useApi> }) {
  return (
    <CrudPanel
      api={api}
      title="Tags"
      listPath={`/admin/tags?tenant_id=${tenantId}`}
      createPath="/admin/tags"
      fields={[
        { name: "name", label: "Name" },
        { name: "category", label: "Category" }
      ]}
      initialValues={{ tenant_id: tenantId }}
    />
  );
}

function Policies({ api }: { api: ReturnType<typeof useApi> }) {
  return (
    <Tabs
      items={[
        { key: "resource", label: "Resource", children: <CrudPolicy api={api} kind="resource" /> },
        { key: "field", label: "Field", children: <CrudPolicy api={api} kind="field" /> }
      ]}
    />
  );
}

function CrudPolicy({ api, kind }: { api: ReturnType<typeof useApi>; kind: "resource" | "field" }) {
  const isField = kind === "field";
  return (
    <CrudPanel
      api={api}
      title={isField ? "Field Policies" : "Resource Policies"}
      listPath={`/admin/${kind}-policies?tenant_id=${tenantId}`}
      createPath={`/admin/${kind}-policies`}
      fields={[
        { name: "subject_type", label: "Subject type" },
        { name: "subject_id", label: "Subject" },
        { name: "effect", label: "Effect" },
        { name: "action", label: "Action" },
        { name: "resource_id", label: "Resource ID" },
        ...(isField ? [{ name: "field_name", label: "Field" }] : [])
      ]}
      initialValues={{ tenant_id: tenantId, action: "read", effect: "allow" }}
    />
  );
}

function Masking({ api }: { api: ReturnType<typeof useApi> }) {
  return (
    <CrudPanel
      api={api}
      title="Masking Policies"
      listPath={`/admin/masking-policies?tenant_id=${tenantId}`}
      createPath="/admin/masking-policies"
      fields={[
        { name: "resource_id", label: "Resource ID" },
        { name: "field_name", label: "Field" },
        { name: "strategy", label: "Strategy" }
      ]}
      initialValues={{ tenant_id: tenantId, strategy: "fixed", config: { replacement: "REDACTED" } }}
    />
  );
}

function ApiKeys({ api }: { api: ReturnType<typeof useApi> }) {
  const state = useData<AnyRecord[]>(() => api.request("/admin/api-keys"), [api.apiKey]);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const create = async () => {
    const values = await form.validateFields();
    const created = await api.request<AnyRecord>("/admin/api-keys", {
      method: "POST",
      body: JSON.stringify({ name: values.name, scopes: values.scopes })
    });
    Modal.info({ title: "New API key", content: <Typography.Text copyable>{created.api_key}</Typography.Text> });
    setOpen(false);
    state.reload();
  };
  return (
    <Space direction="vertical" size={12} className="full">
      <Button type="primary" onClick={() => setOpen(true)}>Create key</Button>
      <DataPanel title="API Keys" state={state} columns={columnsFromRows(state.data || [])} />
      <Drawer title="Create API key" open={open} onClose={() => setOpen(false)} extra={<Button type="primary" onClick={create}>Save</Button>}>
        <Form form={form} layout="vertical" initialValues={{ scopes: ["runtime"] }}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="scopes" label="Scopes"><Select mode="tags" /></Form.Item>
        </Form>
      </Drawer>
    </Space>
  );
}

function McpSetup({ api }: { api: ReturnType<typeof useApi> }) {
  const state = useData<AnyRecord>(() => api.request("/admin/mcp/setup"), [api.apiKey]);
  if (state.error) return <Alert type="error" message={state.error} />;
  if (!state.data) return <Empty />;
  return (
    <Descriptions bordered column={1} size="small">
      <Descriptions.Item label="Tool URL">{state.data.tool_url}</Descriptions.Item>
      <Descriptions.Item label="API key header">{state.data.api_key_header}</Descriptions.Item>
      <Descriptions.Item label="Tools">{state.data.tools.map((tool: string) => <Tag key={tool}>{tool}</Tag>)}</Descriptions.Item>
    </Descriptions>
  );
}

function CrudPanel({
  api,
  title,
  listPath,
  createPath,
  fields,
  initialValues
}: {
  api: ReturnType<typeof useApi>;
  title: string;
  listPath: string;
  createPath: string;
  fields: Array<{ name: string; label: string }>;
  initialValues: AnyRecord;
}) {
  const state = useData<AnyRecord[]>(() => api.request(listPath), [api.apiKey, listPath]);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const save = async () => {
    const values = await form.validateFields();
    await api.request(createPath, {
      method: "POST",
      body: JSON.stringify({ ...initialValues, ...values })
    });
    message.success("Saved");
    setOpen(false);
    state.reload();
  };
  return (
    <Space direction="vertical" size={12} className="full">
      <Button type="primary" onClick={() => setOpen(true)}>Create</Button>
      <DataPanel title={title} state={state} columns={columnsFromRows(state.data || [])} />
      <Drawer title={`Create ${title}`} open={open} onClose={() => setOpen(false)} extra={<Button type="primary" onClick={save}>Save</Button>}>
        <Form form={form} layout="vertical" initialValues={initialValues}>
          {fields.map((field) => (
            <Form.Item key={field.name} name={field.name} label={field.label} rules={[{ required: field.name !== "category" }]}>
              <Input />
            </Form.Item>
          ))}
        </Form>
      </Drawer>
    </Space>
  );
}

function DataPanel({
  title,
  state,
  columns,
  onRow
}: {
  title: string;
  state: { data: AnyRecord[] | null; loading: boolean; error: string | null; reload: () => void };
  columns: ColumnsType<AnyRecord>;
  onRow?: (row: AnyRecord) => React.HTMLAttributes<HTMLElement>;
}) {
  const count = state.data?.length || 0;
  return (
    <section className="panel">
      <div className="panel-head">
        <Typography.Title level={4}>{title}</Typography.Title>
        <Space><Tag>{count} rows</Tag><Button onClick={state.reload}>Refresh</Button></Space>
      </div>
      {state.error ? <Alert type="error" message={state.error} /> : (
        <Table size="small" rowKey={(row) => row.id || JSON.stringify(row)} loading={state.loading} dataSource={state.data || []} columns={columns} onRow={onRow} pagination={{ pageSize: 8 }} />
      )}
    </section>
  );
}

function columnsFromRows(rows: AnyRecord[]): ColumnsType<AnyRecord> {
  const keys = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 8);
  return keys.map((key) => ({
    title: key,
    dataIndex: key,
    ellipsis: true,
    render: (value: unknown) => typeof value === "object" && value !== null ? JSON.stringify(value) : String(value ?? "")
  }));
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(<App />);
