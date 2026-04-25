import { Alert, Button, Collapse, Input, Tabs, Typography } from "antd";

export type AdminOnboardingCopy = {
  /** Main heading shown when the console has no authenticated admin key yet. */
  title: string;
  /** Introductory summary explaining why the key is needed. */
  description: string;
  /** Label for the admin key input field. */
  inputLabel: string;
  /** Placeholder for the admin key input field. */
  inputPlaceholder: string;
  /** Primary CTA text used to enter the console after a key is supplied. */
  continueLabel: string;
  /** Title for the collapsible initialization guidance. */
  methodsTitle: string;
  /** Initialization methods grouped by deployment style. */
  methods: Array<{
    key: string;
    label: string;
    description: string;
    commandValue: string;
  }>;
  /** Title used by the authentication failure alert. */
  authErrorTitle: string;
};

export function AdminOnboarding({
  apiKey,
  authError,
  validating,
  onApiKeyChange,
  onContinue,
  brandLabel,
  languageControl,
  copy,
}: {
  apiKey: string;
  authError: string | null;
  validating: boolean;
  onApiKeyChange: (value: string) => void;
  onContinue: () => void;
  brandLabel: string;
  languageControl?: React.ReactNode;
  copy: AdminOnboardingCopy;
}) {
  /** Guide operators through bootstrap before the authenticated console becomes available. */

  const isDisabled = apiKey.trim().length === 0 || validating;

  return (
    <section className="admin-login-page">
      <div className="admin-login-card">
        <div className="admin-login-toolbar">
          <Typography.Text className="admin-login-brand">{brandLabel}</Typography.Text>
          {languageControl}
        </div>
        <div className="admin-login-header">
          <Typography.Title level={1}>{copy.title}</Typography.Title>
          <Typography.Paragraph>{copy.description}</Typography.Paragraph>
        </div>
        <section className="admin-login-panel">
          {authError ? (
            <Alert
              showIcon
              type="warning"
              message={copy.authErrorTitle}
              description={authError}
            />
          ) : null}
          <div className="admin-login-field">
            <Typography.Text className="admin-login-label">{copy.inputLabel}</Typography.Text>
            <Input.Password
              autoComplete="off"
              size="large"
              value={apiKey}
              disabled={validating}
              placeholder={copy.inputPlaceholder}
              onChange={(event) => onApiKeyChange(event.target.value)}
              onPressEnter={() => {
                if (!isDisabled) {
                  onContinue();
                }
              }}
            />
          </div>
          <Button type="primary" size="large" block disabled={isDisabled} loading={validating} onClick={onContinue}>
            {copy.continueLabel}
          </Button>
          <Collapse
            ghost
            className="admin-login-collapse"
            items={[
              {
                key: "init-methods",
                label: copy.methodsTitle,
                children: (
                  <Tabs
                    defaultActiveKey={copy.methods[0]?.key}
                    items={copy.methods.map((method) => ({
                      key: method.key,
                      label: method.label,
                      children: (
                        <div className="admin-login-method">
                          <Typography.Paragraph>{method.description}</Typography.Paragraph>
                          <Input.TextArea
                            autoSize={{ minRows: 3, maxRows: 6 }}
                            readOnly
                            value={method.commandValue}
                          />
                        </div>
                      ),
                    }))}
                  />
                ),
              },
            ]}
          />
        </section>
      </div>
    </section>
  );
}
