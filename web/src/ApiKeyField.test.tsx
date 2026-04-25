// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiKeyField } from "./ApiKeyField";

afterEach(() => {
  cleanup();
});

describe("ApiKeyField", () => {
  it("hides the API key value by default and exposes a visibility toggle", () => {
    const onChange = vi.fn();

    render(
      <ApiKeyField
        label="API 密钥"
        value="secret-key"
        onChange={onChange}
        showLabel="显示 API 密钥"
        hideLabel="隐藏 API 密钥"
      />,
    );

    const input = screen.getByLabelText("API 密钥");
    expect(input).toHaveAttribute("type", "password");

    fireEvent.click(screen.getByLabelText("显示 API 密钥"));
    expect(screen.getByLabelText("API 密钥")).toHaveAttribute("type", "text");

    fireEvent.change(screen.getByLabelText("API 密钥"), { target: { value: "updated-key" } });
    expect(onChange).toHaveBeenCalledWith("updated-key");
  });
});
