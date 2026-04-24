// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CompactActionButton } from "./CompactActionButton";

describe("CompactActionButton", () => {
  it("renders an icon-only button with an accessible label", () => {
    render(
      <CompactActionButton
        title="Linked assets"
        icon={<span aria-hidden="true">i</span>}
        onClick={vi.fn()}
      />,
    );

    const button = screen.getByRole("button", { name: "Linked assets" });
    expect(button).toBeTruthy();
    expect(button).toHaveAccessibleName("Linked assets");
    expect(button).not.toHaveTextContent("Linked assets");
  });
});
