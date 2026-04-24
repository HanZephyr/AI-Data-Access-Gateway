import { Alert, Button, Input, Space, Typography } from "antd";

export type AdminOnboardingCopy = {
  /** Main heading shown when the console has no authenticated admin key yet. */
  title: string;
  /** Introductory summary explaining why the key is needed. */
  description: string;
  /** Label displayed above the bootstrap command. */
  commandLabel: string;
  /** Exact command operators should run to create an admin key. */
  commandValue: string;
  /** Label for the admin key input field. */
  inputLabel: string;
  /** Placeholder for the admin key input field. */
  inputPlaceholder: string;
  /** Primary CTA text used to enter the console after a key is supplied. */
  continueLabel: string;
  /** Title for the recommended setup sequence. */
  hintTitle: string;
  /** Ordered setup steps shown beside the command. */
  hintSteps: string[];
  /** Title used by the authentication failure alert. */
  authErrorTitle: string;
};

export function AdminOnboarding({
  apiKey,
  authError,
  onApiKeyChange,
  onContinue,
  copy,
}: {
  apiKey: string;
  authError: string | null;
  onApiKeyChange: (value: string) => void;
  onContinue: () => void;
  copy: AdminOnboardingCopy;
}) {
  /** Guide operators through bootstrap before the authenticated console becomes available. */

  const isDisabled = apiKey.trim().length === 0;

  return (
    <section className="admin-onboarding">
      <div className="admin-onboarding-hero">
        <Typography.Text className="admin-onboarding-kicker">ADG</Typography.Text>
        <Typography.Title level={1}>{copy.title}</Typography.Title>
        <Typography.Paragraph>{copy.description}</Typography.Paragraph>
      </div>
      <div className="admin-onboarding-grid">
        <section className="admin-onboarding-panel">
          <Typography.Text className="admin-onboarding-label">{copy.commandLabel}</Typography.Text>
          <Input.TextArea
            autoSize={{ minRows: 3, maxRows: 5 }}
            readOnly
            value={copy.commandValue}
          />
          <div className="admin-onboarding-hints">
            <Typography.Text className="admin-onboarding-label">{copy.hintTitle}</Typography.Text>
            <ol>
              {copy.hintSteps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
        </section>
        <section className="admin-onboarding-panel">
          {authError ? (
            <Alert
              showIcon
              type="warning"
              message={copy.authErrorTitle}
              description={authError}
            />
          ) : null}
          <Space direction="vertical" size={12} className="full">
            <Typography.Text className="admin-onboarding-label">{copy.inputLabel}</Typography.Text>
            <Input.Password
              autoComplete="off"
              value={apiKey}
              placeholder={copy.inputPlaceholder}
              onChange={(event) => onApiKeyChange(event.target.value)}
              onPressEnter={() => {
                if (!isDisabled) {
                  onContinue();
                }
              }}
            />
            <Button type="primary" size="large" disabled={isDisabled} onClick={onContinue}>
              {copy.continueLabel}
            </Button>
          </Space>
        </section>
      </div>
    </section>
  );
}
