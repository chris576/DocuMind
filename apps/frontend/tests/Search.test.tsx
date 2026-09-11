import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Search from "../src/pages/Search";
import { searchDocuments } from "../src/api";

vi.mock("../src/api", () => ({
  searchDocuments: vi.fn(),
}));

const mockedSearch = vi.mocked(searchDocuments);

function renderSearch() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <Search />
    </QueryClientProvider>,
  );
}

describe("Search", () => {
  beforeEach(() => {
    mockedSearch.mockReset();
  });

  it("renders the search form", () => {
    renderSearch();
    expect(screen.getByPlaceholderText(/suchbegriff/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /suchen/i })).toBeInTheDocument();
  });

  it("submits the query and renders results", async () => {
    mockedSearch.mockResolvedValue([
      {
        title: "Rechnung",
        correspondent: "ACME",
        date: "2024-01-01",
        score: 0.95,
        crossScore: 0.8,
        snippet: "Zahlungsziel 14 Tage.",
        docId: 1,
      },
    ]);
    renderSearch();

    fireEvent.change(screen.getByPlaceholderText(/suchbegriff/i), {
      target: { value: "Rechnung" },
    });
    fireEvent.click(screen.getByRole("button", { name: /suchen/i }));

    await waitFor(() =>
      expect(screen.getByText("Rechnung")).toBeInTheDocument(),
    );
    expect(mockedSearch).toHaveBeenCalled();
    expect(mockedSearch.mock.calls[0][0]).toEqual({ query: "Rechnung" });
  });

  it("shows an error when the search fails", async () => {
    mockedSearch.mockRejectedValue(new Error("down"));
    renderSearch();

    fireEvent.change(screen.getByPlaceholderText(/suchbegriff/i), {
      target: { value: "x" },
    });
    fireEvent.click(screen.getByRole("button", { name: /suchen/i }));

    await waitFor(() =>
      expect(screen.getByText(/fehler bei der suche/i)).toBeInTheDocument(),
    );
  });
});
