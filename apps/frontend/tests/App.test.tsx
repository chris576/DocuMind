import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import App from "../src/App";

vi.mock("../src/api", () => ({
  getIngestionStatus: vi.fn().mockResolvedValue({ initialized: true }),
  getRetrievalStatus: vi.fn().mockResolvedValue({ ready: true }),
  getGenerationStatus: vi.fn().mockResolvedValue({ status: "ok" }),
  searchDocuments: vi.fn(),
  askQuestion: vi.fn(),
  runIngestion: vi.fn(),
  runIngestionSync: vi.fn(),
}));

describe("App", () => {
  it("redirects / to the dashboard", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/"]}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
  });
});
