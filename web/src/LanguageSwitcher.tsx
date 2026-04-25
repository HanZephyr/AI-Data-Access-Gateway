import { GlobalOutlined } from "@ant-design/icons";
import { Select, Tooltip } from "antd";

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
  return (
    <div className={["language-switcher", className].filter(Boolean).join(" ")}>
      <Tooltip title={label}>
        <span className="language-switcher-icon" aria-hidden="true">
          <GlobalOutlined />
        </span>
      </Tooltip>
      <Select
        aria-label={label}
        value={value}
        options={options}
        onChange={(nextValue) => onChange(nextValue as Language)}
      />
    </div>
  );
}
