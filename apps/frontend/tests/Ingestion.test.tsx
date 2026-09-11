import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Ingestion from "../src/pages/Ingestion";
import {
  getIngestionStatus,
  runIngestion,
  runIngestionSync,
} from "../src/api";

vi.mock("../src/api", () => ({
  getIngestionStatus: vi.fn(),
  runIngestion: vi.fn(),
  runIngestionSync: vi.fn(),
}));

const mockedStatus = vi.mocked(getIngestionStatus);
const mockedRun = vi.mocked(runIngestion);
const mockedRunSync = vi.mocked(runIngestionSync);

function renderIngestion() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <Ingestion />
    </QueryClientProvider>,
  );
}

describe("Ingestion", () => {
  beforeEach(() => {
    mockedStatus.mockReset();
    mockedRun.mockReset();
    mockedRunSync.mockReset();
    mockedStatus.mockResolvedValue({ initialized: true });
  });

  it("renders the ingestion controls", () => {
    renderIngestion();
    expect(
      screen.getByRole("button", { name: /indexierung starten/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /synchron ausführen/i }),
    ).toBeInTheDocument();
  });

  it("triggers background ingestion on button click", async () => {
    mockedRun.mockResolvedValue({ status: "started" });
    renderIngestion();

    fireEvent.click(
      screen.getByRole("button", { name: /indexierung starten/i }),
    );

    await waitFor(() => expect(mockedRun).toHaveBeenCalled());
    expect(mockedRun.mock.calls[0][0]).toEqual({
      force: false,
      checkNew: true,
    });
  });

  it("triggers synchronous ingestion on button click", async () => {
    mockedRunSync.mockResolvedValue({ status: "completed" });
    renderIngestion();

    fireEvent.click(
      screen.getByRole("button", { name: /synchron ausführen/i }),
    );

    await waitFor(() => expect(mockedRunSync).toHaveBeenCalled());
    expect(mockedRunSync.mock.calls[0][0]).toEqual({
      force: false,
      checkNew: true,
    });
  });

  it("shows an error when ingestion fails", async () => {
    mockedRun.mockRejectedValue(new Error("down"));
    renderIngestion();

    fireEvent.click(
      screen.getByRole("button", { name: /indexierung starten/i }),
    );

    await waitFor(() =>
      expect(screen.getByText(/ingestion fehlgeschlagen/i)).toBeInTheDocument(),
    );
  });
});
