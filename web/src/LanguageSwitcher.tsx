import { CheckOutlined, DownOutlined, GlobalOutlined } from "@ant-design/icons";
import { Button, Dropdown } from "antd";

import type { Language } from "./language";

export function LanguageSwitcher({
  label,
  value,
  options,
  onChange,
  className,
}: {
  label: string;
  value: Language;
  options: Array<{ value: Language; label: string }>;
  onChange: (value: Language) => void;
  className?: string;
}) {
  const activeOption = options.find((option) => option.value === value);

  return (
    <Dropdown
      trigger={["click"]}
      menu={{
        selectable: true,
        selectedKeys: [value],
        items: options.map((option) => ({
          key: option.value,
          label: option.label,
          icon: option.value === value ? <CheckOutlined /> : <span className="language-switcher-menu-spacer" />,
        })),
        onClick: ({ key }) => onChange(key as Language),
      }}
    >
      <Button
        aria-label={label}
        className={["language-switcher", className].filter(Boolean).join(" ")}
      >
        <span className="language-switcher-content">
          <span className="language-switcher-leading">
            <GlobalOutlined />
            <span>{label}</span>
          </span>
          <span className="language-switcher-value">{activeOption?.label || value}</span>
        </span>
        <DownOutlined className="language-switcher-caret" />
      </Button>
    </Dropdown>
  );
}
