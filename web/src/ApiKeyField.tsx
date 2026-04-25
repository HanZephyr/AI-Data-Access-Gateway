import React, { useState } from "react";
import { EyeInvisibleOutlined, EyeOutlined } from "@ant-design/icons";
import { Button, Input, Space, Tooltip } from "antd";

export function ApiKeyField({
  label,
  value,
  onChange,
  showLabel,
  hideLabel,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  showLabel: string;
  hideLabel: string;
}) {
  const [visible, setVisible] = useState(false);
  const toggleLabel = visible ? hideLabel : showLabel;

  return (
    <Space.Compact className="key-input">
      <Button>{label}</Button>
      <Input
        aria-label={label}
        id="adg-api-key"
        name="adg-api-key"
        autoComplete="off"
        type={visible ? "text" : "password"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <Tooltip title={toggleLabel}>
        <Button
          aria-label={toggleLabel}
          icon={visible ? <EyeInvisibleOutlined /> : <EyeOutlined />}
          onClick={() => setVisible((current) => !current)}
        />
      </Tooltip>
    </Space.Compact>
  );
}
