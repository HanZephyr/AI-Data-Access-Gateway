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
type FieldConfig = {
  name: string;
  label: string;
  input?: "text" | "textarea" | "json" | "number" | "tags" | "select";
  required?: boolean;
  options?: string[];
};

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
      <AntApp>
        <ConsoleApp />
      </AntApp>
    </ConfigProvider>
  );
}

function ConsoleApp() {
  const [page, setPage] = useState<PageKey>("overview");
  const api = useApi();
  return (
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
              autoComplete="off"
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
  const state = useData<AnyRecord[]>(() => (path === "__empty__" ? Promise.resolve([]) : api.request(path)), [api.apiKey, path]);
  const [selected, setSelected] = useState<AnyRecord | null>(null);
  const columns = columnsFromRows(state.data || []);
  return (
    <>
      <DataPanel
        title={title}
        state={state}
        columns={columns}
        actions={(row) => <IconAction title="View" icon={<EyeOutlined />} onClick={() => setSelected(row)} />}
      />
      <RecordDetails record={selected} title={title} onClose={() => setSelected(null)} />
    </>
  );
}

function Datasources({ api }: { api: ReturnType<typeof useApi> }) {
  return (
    <CrudPanel
      api={api}
      title="Data Sources"
      listPath="/admin/datasources"
      createPath="/admin/datasources"
      updatePath={(row) => `/admin/datasources/${row.id}`}
      deletePath={(row) => `/admin/datasources/${row.id}`}
      fields={[
        { name: "tenant_id", label: "Tenant ID", required: true },
        { name: "name", label: "Name", required: true },
        { name: "type", label: "Type", input: "select", options: ["postgres", "mysql", "doris"], required: true },
        { name: "status", label: "Status", input: "select", options: ["active", "disabled"], required: true },
        { name: "config", label: "Config", input: "json", required: true }
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
        title="Resources"
        listPath={`/admin/resources?tenant_id=${tenantId}`}
        updatePath={(row) => `/admin/resources/${row.id}`}
        deletePath={(row) => `/admin/resources/${row.id}`}
        fields={[
          { name: "display_name", label: "Display name" },
          { name: "query_language", label: "Query language" }
        ]}
        initialValues={{}}
        onRow={(row) => ({ onClick: () => setResourceId(row.id) })}
        stateOverride={state}
      />
      <EndpointTable api={api} title="Fields" path={resourceId ? `/admin/resources/${resourceId}/fields` : "__empty__"} />
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
      updatePath={(row) => `/admin/tags/${row.id}`}
      deletePath={(row) => `/admin/tags/${row.id}`}
      fields={[
        { name: "name", label: "Name", required: true },
        { name: "category", label: "Category" },
        { name: "description", label: "Description", input: "textarea" }
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
      updatePath={(row) => `/admin/${kind}-policies/${row.id}`}
      deletePath={(row) => `/admin/${kind}-policies/${row.id}`}
      fields={[
        { name: "subject_type", label: "Subject type", required: true },
        { name: "subject_id", label: "Subject", required: true },
        { name: "effect", label: "Effect", input: "select", options: ["allow", "deny"], required: true },
        { name: "action", label: "Action", required: true },
        { name: "resource_id", label: "Resource ID" },
        ...(isField ? [{ name: "field_name", label: "Field", required: true }] : []),
        ...(!isField ? [{ name: "tag_id", label: "Tag ID" }] : []),
        { name: "priority", label: "Priority", input: "number" as const },
        { name: "status", label: "Status", input: "select" as const, options: ["active", "disabled"] }
      ]}
      initialValues={{ tenant_id: tenantId, action: "read", effect: "allow", priority: 0, status: "active" }}
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
      updatePath={(row) => `/admin/masking-policies/${row.id}`}
      deletePath={(row) => `/admin/masking-policies/${row.id}`}
      fields={[
        { name: "resource_id", label: "Resource ID", required: true },
        { name: "field_name", label: "Field", required: true },
        { name: "subject_type", label: "Subject type" },
        { name: "subject_id", label: "Subject" },
        { name: "strategy", label: "Strategy", input: "select", options: ["fixed", "partial", "hash", "reversible"], required: true },
        { name: "config", label: "Config", input: "json", required: true },
        { name: "status", label: "Status", input: "select", options: ["active", "disabled"] }
      ]}
      initialValues={{ tenant_id: tenantId, strategy: "fixed", config: { replacement: "REDACTED" }, status: "active" }}
    />
  );
}

function ApiKeys({ api }: { api: ReturnType<typeof useApi> }) {
  const { message: messageApi, modal } = AntApp.useApp();
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
    modal.info({ title: "New API key", content: <Typography.Text copyable>{created.api_key}</Typography.Text> });
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
    messageApi.success("Saved");
    setEditing(null);
    state.reload();
  };
  const revoke = async (row: AnyRecord) => {
    await api.request(`/admin/api-keys/${row.id}/revoke`, { method: "POST" });
    messageApi.success("Revoked");
    state.reload();
  };
  return (
    <Space direction="vertical" size={12} className="full">
      <Button type="primary" onClick={() => setOpen(true)}>Create key</Button>
      <DataPanel
        title="API Keys"
        state={state}
        columns={columnsFromRows(state.data || [])}
        actions={(row) => (
          <Space size={4}>
            <IconAction title="View" icon={<EyeOutlined />} onClick={() => setSelected(row)} />
            <IconAction
              title="Edit"
              icon={<EditOutlined />}
              onClick={() => {
                setEditing(row);
                editForm.setFieldsValue(row);
              }}
            />
            <Popconfirm title="Revoke this key?" onConfirm={() => revoke(row)}>
              <Button size="small" icon={<StopOutlined />} />
            </Popconfirm>
          </Space>
        )}
      />
      <RecordDetails record={selected} title="API Key" onClose={() => setSelected(null)} />
      <Drawer title="Create API key" open={open} onClose={() => setOpen(false)} extra={<Button type="primary" onClick={create}>Save</Button>}>
        <Form form={form} layout="vertical" initialValues={{ scopes: ["runtime"] }}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input autoComplete="off" /></Form.Item>
          <Form.Item name="scopes" label="Scopes"><Select mode="tags" /></Form.Item>
        </Form>
      </Drawer>
      <Drawer title="Edit API key" open={Boolean(editing)} onClose={() => setEditing(null)} extra={<Button type="primary" onClick={edit}>Save</Button>}>
        <Form form={editForm} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input autoComplete="off" /></Form.Item>
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
  updatePath,
  deletePath,
  fields,
  initialValues,
  onRow,
  stateOverride
}: {
  api: ReturnType<typeof useApi>;
  title: string;
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
      body: JSON.stringify(normalizeValues({ ...initialValues, ...values }, fields))
    });
    messageApi.success("Saved");
    setOpen(false);
    state.reload();
  };
  const update = async () => {
    if (!editing || !updatePath) return;
    const values = await editForm.validateFields();
    await api.request(updatePath(editing), {
      method: "PATCH",
      body: JSON.stringify(normalizeValues(values, fields))
    });
    messageApi.success("Saved");
    setEditing(null);
    state.reload();
  };
  const remove = async (row: AnyRecord) => {
    if (!deletePath) return;
    await api.request(deletePath(row), { method: "DELETE" });
    messageApi.success("Deleted");
    state.reload();
  };
  return (
    <Space direction="vertical" size={12} className="full">
      {createPath ? <Button type="primary" onClick={() => { form.resetFields(); form.setFieldsValue(toFormValues(initialValues, fields)); setOpen(true); }}>Create</Button> : null}
      <DataPanel
        title={title}
        state={state}
        columns={columnsFromRows(state.data || [])}
        onRow={onRow}
        actions={(row) => (
          <Space size={4} onClick={(event) => event.stopPropagation()}>
            <IconAction title="View" icon={<EyeOutlined />} onClick={() => setSelected(row)} />
            {updatePath ? (
              <IconAction
                title="Edit"
                icon={<EditOutlined />}
                onClick={() => {
                  setEditing(row);
                  editForm.setFieldsValue(toFormValues(row, fields));
                }}
              />
            ) : null}
            {deletePath ? (
              <Popconfirm title={`Delete ${title}?`} onConfirm={() => remove(row)}>
                <Button size="small" icon={<DeleteOutlined />} />
              </Popconfirm>
            ) : null}
          </Space>
        )}
      />
      <RecordDetails record={selected} title={title} onClose={() => setSelected(null)} />
      <Drawer title={`Create ${title}`} open={open} onClose={() => setOpen(false)} extra={<Button type="primary" onClick={save}>Save</Button>}>
        <Form form={form} layout="vertical" initialValues={toFormValues(initialValues, fields)}>
          {fields.map(renderField)}
        </Form>
      </Drawer>
      <Drawer title={`Edit ${title}`} open={Boolean(editing)} onClose={() => setEditing(null)} extra={<Button type="primary" onClick={update}>Save</Button>}>
        <Form form={editForm} layout="vertical">
          {fields.map(renderField)}
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
        <Space><Tag>{count} rows</Tag><Button onClick={state.reload}>Refresh</Button></Space>
      </div>
      {state.error ? <Alert type="error" message={state.error} /> : (
        <Table size="small" rowKey={(row) => row.id || JSON.stringify(row)} loading={state.loading} dataSource={state.data || []} columns={tableColumns} onRow={onRow} pagination={{ pageSize: 8 }} scroll={{ x: true }} />
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
  return (
    <Drawer title={`${title} Details`} open={Boolean(record)} onClose={onClose} width={560}>
      {record ? (
        <Descriptions bordered column={1} size="small">
          {Object.entries(record).map(([key, value]) => (
            <Descriptions.Item key={key} label={key}>
              <Typography.Text copyable={typeof value === "string"}>
                {typeof value === "object" && value !== null ? JSON.stringify(value) : String(value ?? "")}
              </Typography.Text>
            </Descriptions.Item>
          ))}
        </Descriptions>
      ) : null}
    </Drawer>
  );
}

function renderField(field: FieldConfig) {
  const rules = field.required ? [{ required: true, message: `${field.label} is required` }] : undefined;
  let control: React.ReactNode = <Input autoComplete="off" />;
  if (field.input === "textarea" || field.input === "json") {
    control = <Input.TextArea autoComplete="off" autoSize={{ minRows: 3, maxRows: 8 }} />;
  } else if (field.input === "number") {
    control = <InputNumber className="full" />;
  } else if (field.input === "tags") {
    control = <Select mode="tags" />;
  } else if (field.input === "select") {
    control = <Select options={(field.options || []).map((value) => ({ label: value, value }))} />;
  }
  return (
    <Form.Item key={field.name} name={field.name} label={field.label} rules={rules}>
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

function normalizeValues(values: AnyRecord, fields: FieldConfig[]) {
  const result = { ...values };
  for (const field of fields) {
    if (field.input === "json" && typeof result[field.name] === "string") {
      try {
        result[field.name] = JSON.parse(result[field.name]);
      } catch (error) {
        throw new Error(`${field.label} must be valid JSON`);
      }
    }
  }
  return result;
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(<App />);
