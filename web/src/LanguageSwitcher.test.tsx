// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LanguageSwitcher } from "./LanguageSwitcher";

afterEach(() => {
  cleanup();
});

describe("LanguageSwitcher", () => {
  it("shows a language hint icon and lets the user choose a language", () => {
    const onChange = vi.fn();

    render(
      <LanguageSwitcher
        label="切换界面语言"
        value="zh-CN"
        options={[
          { value: "zh-CN", label: "简体中文" },
          { value: "zh-TW", label: "繁體中文" },
          { value: "en-US", label: "English" },
        ]}
        onChange={onChange}
      />,
    );

    expect(screen.getByRole("combobox", { name: "切换界面语言" })).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole("combobox"));
    fireEvent.click(screen.getByText("English"));

    expect(onChange).toHaveBeenCalledWith("en-US");
  });
});
