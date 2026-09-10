import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import Search from "../src/pages/Search";

describe("Search", () => {
  it("renders the search form", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <Search />
      </QueryClientProvider>,
    );

    expect(screen.getByPlaceholderText(/suchbegriff/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /suchen/i })).toBeTruthy();
  });
});
