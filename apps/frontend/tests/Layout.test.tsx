import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import Layout from "../src/components/Layout";

describe("Layout", () => {
  it("renders the brand and navigation links", () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>,
    );

    expect(screen.getByText("DocuMind")).toBeInTheDocument();
    for (const name of ["Dashboard", "Suche", "Frage/Antwort", "Ingestion"]) {
      expect(screen.getByRole("link", { name: new RegExp(name) })).toBeInTheDocument();
    }
  });

  it("toggles dark mode", () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>,
    );

    const button = screen.getByRole("button");
    expect(button).toHaveTextContent("🌙");

    fireEvent.click(button);

    expect(button).toHaveTextContent("☀️");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
