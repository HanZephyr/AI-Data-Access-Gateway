// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Button } from "antd";

import { AdminOnboarding } from "./AdminOnboarding";

afterEach(() => {
  cleanup();
});

describe("AdminOnboarding", () => {
  it("guides operators to initialize an admin API key before entering the console", () => {
    render(
      <AdminOnboarding
        apiKey=""
        authError={null}
        validating={false}
        onApiKeyChange={() => undefined}
        onContinue={() => undefined}
        brandLabel="AI 数据库连接网关"
        copy={{
          title: "管理员登录",
          description: "请输入管理员 API Key 进入控制台。",
          inputLabel: "管理员 API Key",
          inputPlaceholder: "输入 init-admin 输出的密钥",
          continueLabel: "登录控制台",
          methodsTitle: "初始化管理员 API Key",
          methods: [
            {
              key: "uv",
              label: "uv",
              description: "适合直接使用 uv 管理依赖和命令的部署方式。",
              commandValue: "uv run --extra dev init-admin --database-url sqlite:///./data/adg-control-plane.db",
            },
            {
              key: "python",
              label: "Python",
              description: "适合原生 Python 环境。",
              commandValue: "python -m adg.control_plane.bootstrap --database-url sqlite:///./data/adg-control-plane.db",
            },
            {
              key: "docker",
              label: "Docker",
              description: "适合通过 Docker Compose 启动的部署方式。",
              commandValue: "docker exec -it ai-data-access-gateway-backend-1 init-admin",
            }
          ],
          authErrorTitle: "认证失败",
        }}
      />,
    );

    expect(screen.getByText("管理员登录")).toBeInTheDocument();
    expect(screen.getByText("AI 数据库连接网关")).toBeInTheDocument();
    expect(screen.getByText("初始化管理员 API Key")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "登录控制台" })).toBeDisabled();
  });

  it("renders a language switcher slot on the login page", () => {
    render(
      <AdminOnboarding
        apiKey=""
        authError={null}
        validating={false}
        onApiKeyChange={() => undefined}
        onContinue={() => undefined}
        brandLabel="AI 数据库连接网关"
        languageControl={<Button aria-label="切换界面语言">简体中文</Button>}
        copy={{
          title: "管理员登录",
          description: "请输入管理员 API Key 进入控制台。",
          inputLabel: "管理员 API Key",
          inputPlaceholder: "输入 init-admin 输出的密钥",
          continueLabel: "登录控制台",
          methodsTitle: "初始化管理员 API Key",
          methods: [],
          authErrorTitle: "认证失败",
        }}
      />,
    );

    expect(screen.getByLabelText("切换界面语言")).toBeInTheDocument();
  });

  it("shows the docker initialization method after expanding the help panel", () => {
    render(
      <AdminOnboarding
        apiKey=""
        authError={null}
        validating={false}
        onApiKeyChange={() => undefined}
        onContinue={() => undefined}
        brandLabel="AI 数据库连接网关"
        copy={{
          title: "管理员登录",
          description: "请输入管理员 API Key 进入控制台。",
          inputLabel: "管理员 API Key",
          inputPlaceholder: "输入 init-admin 输出的密钥",
          continueLabel: "登录控制台",
          methodsTitle: "初始化管理员 API Key",
          methods: [
            {
              key: "python",
              label: "Python",
              description: "适合原生 Python 环境。",
              commandValue: "python -m adg.control_plane.bootstrap --database-url sqlite:///./data/adg-control-plane.db",
            },
            {
              key: "uv",
              label: "uv",
              description: "适合 uv 环境。",
              commandValue: "uv run --extra dev init-admin --database-url sqlite:///./data/adg-control-plane.db",
            },
            {
              key: "docker",
              label: "Docker",
              description: "适合 Docker Compose 部署。",
              commandValue: "docker exec -it ai-data-access-gateway-backend-1 init-admin",
            }
          ],
          authErrorTitle: "认证失败",
        }}
      />,
    );

    fireEvent.click(screen.getAllByRole("button", { name: /初始化管理员 API Key/ })[0]);
    fireEvent.click(screen.getByRole("tab", { name: "Docker" }));

    expect(
      screen.getByDisplayValue("docker exec -it ai-data-access-gateway-backend-1 init-admin"),
    ).toBeInTheDocument();
  });
});
