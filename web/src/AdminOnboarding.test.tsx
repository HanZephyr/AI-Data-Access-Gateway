// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AdminOnboarding } from "./AdminOnboarding";

describe("AdminOnboarding", () => {
  it("guides operators to initialize an admin API key before entering the console", () => {
    render(
      <AdminOnboarding
        apiKey=""
        authError={null}
        onApiKeyChange={() => undefined}
        onContinue={() => undefined}
        copy={{
          title: "管理员初始化",
          description: "先初始化管理员 API Key，再进入控制台。",
          commandLabel: "初始化命令",
          commandValue: "uv run --extra dev init-admin --database-url sqlite:///./data/adg-control-plane.db",
          inputLabel: "管理员 API Key",
          inputPlaceholder: "输入 init-admin 输出的密钥",
          continueLabel: "进入控制台",
          hintTitle: "推荐流程",
          hintSteps: [
            "先执行 alembic upgrade head。",
            "再执行 init-admin 创建管理员密钥。",
            "把命令输出的密钥粘贴到这里。"
          ],
          authErrorTitle: "认证失败",
        }}
      />,
    );

    expect(screen.getByText("管理员初始化")).toBeInTheDocument();
    expect(screen.getByDisplayValue("uv run --extra dev init-admin --database-url sqlite:///./data/adg-control-plane.db")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "进入控制台" })).toBeDisabled();
  });
});
