import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Settings from "../src/pages/Settings";
import { getConfig, saveConfig } from "../src/api";

vi.mock("../src/api", () => ({
  getConfig: vi.fn(),
  saveConfig: vi.fn(),
}));

const mockedGet = vi.mocked(getConfig);
const mockedSave = vi.mocked(saveConfig);

function renderSettings() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <Settings />
    </QueryClientProvider>,
  );
}

describe("Settings", () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedSave.mockReset();
    mockedGet.mockResolvedValue({ version: 1, llm: { provider: "ollama" } });
  });

  it("loads and displays the config JSON", async () => {
    renderSettings();
    expect(await screen.findByDisplayValue(/ollama/)).toBeInTheDocument();
  });

  it("saves the edited config", async () => {
    mockedSave.mockResolvedValue({ version: 1, llm: { provider: "openai" } });
    renderSettings();

    const textarea = await screen.findByDisplayValue(/ollama/);
    fireEvent.change(textarea, {
      target: {
        value: JSON.stringify({ version: 1, llm: { provider: "openai" } }),
      },
    });
    fireEvent.click(screen.getByRole("button", { name: /speichern/i }));

    await waitFor(() => expect(mockedSave).toHaveBeenCalled());
    expect(mockedSave.mock.calls[0][0]).toEqual({
      version: 1,
      llm: { provider: "openai" },
    });
  });
});
