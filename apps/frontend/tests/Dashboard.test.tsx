import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Dashboard from "../src/pages/Dashboard";
import {
  getGenerationStatus,
  getIngestionStatus,
  getRetrievalStatus,
} from "../src/api";

vi.mock("../src/api", () => ({
  getIngestionStatus: vi.fn(),
  getRetrievalStatus: vi.fn(),
  getGenerationStatus: vi.fn(),
}));

const mockedIngestion = vi.mocked(getIngestionStatus);
const mockedRetrieval = vi.mocked(getRetrievalStatus);
const mockedGeneration = vi.mocked(getGenerationStatus);

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>,
  );
}

describe("Dashboard", () => {
  beforeEach(() => {
    mockedIngestion.mockReset();
    mockedRetrieval.mockReset();
    mockedGeneration.mockReset();
  });

  it("renders the three pipeline status cards", async () => {
    mockedIngestion.mockResolvedValue({ initialized: true });
    mockedRetrieval.mockResolvedValue({ ready: true });
    mockedGeneration.mockResolvedValue({ status: "ok" });

    renderDashboard();

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(await screen.findByText("Ingestion")).toBeInTheDocument();
    expect(screen.getByText("Retrieval")).toBeInTheDocument();
    expect(screen.getByText("Generation")).toBeInTheDocument();
  });

  it("renders status data once loaded", async () => {
    mockedIngestion.mockResolvedValue({ initialized: true });
    mockedRetrieval.mockResolvedValue({ ready: true });
    mockedGeneration.mockResolvedValue({ status: "ok" });

    renderDashboard();

    expect(await screen.findByText(/initialized/)).toBeInTheDocument();
  });

  it("marks unreachable pipelines as errors", async () => {
    mockedIngestion.mockRejectedValue(new Error("down"));
    mockedRetrieval.mockRejectedValue(new Error("down"));
    mockedGeneration.mockRejectedValue(new Error("down"));

    renderDashboard();

    expect(await screen.findAllByText(/nicht erreichbar/)).toHaveLength(3);
  });
});
