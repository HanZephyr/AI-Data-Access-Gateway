import React from "react";
import { Button, Tooltip } from "antd";

export function CompactActionButton({
  title,
  icon,
  onClick,
}: {
  title: string;
  icon: React.ReactNode;
  onClick: () => void;
}) {
  /** Render an icon-only action button with tooltip and accessible label text. */

  return (
    <Tooltip title={title}>
      <Button
        size="small"
        icon={icon}
        aria-label={title}
        onClick={(event) => {
          event.stopPropagation();
          onClick();
        }}
      />
    </Tooltip>
  );
}
