import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import Ask from "../src/pages/Ask";

function mockStream(chunks: string[]) {
  const encoder = new TextEncoder();
  let i = 0;
  const reader = {
    async read() {
      if (i >= chunks.length) {
        return { done: true, value: undefined };
      }
      return { done: false, value: encoder.encode(chunks[i++]) };
    },
  };
  const response = {
    ok: true,
    status: 200,
    body: { getReader: () => reader },
  };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
}

describe("Ask", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the form", () => {
    render(<Ask />);
    expect(screen.getByPlaceholderText(/deine frage/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /fragen/i })).toBeInTheDocument();
  });

  it("streams and reassembles the answer from SSE chunks", async () => {
    // Chunks zerlegt über mehrere read()-Aufrufe, um die Puffer-Logik zu testen.
    mockStream([
      "data: Das ",
      "ist ",
      "die ",
      "Antwort.\n\n",
      "data: [DONE]\n\n",
    ]);
    render(<Ask />);

    fireEvent.change(screen.getByPlaceholderText(/deine frage/i), {
      target: { value: "Frage" },
    });
    fireEvent.click(screen.getByRole("button", { name: /fragen/i }));

    await waitFor(() =>
      expect(screen.getByText(/das ist die antwort/i)).toBeInTheDocument(),
    );
  });

  it("shows an error on [ERROR] payload", async () => {
    mockStream(["data: [ERROR] kaputt\n\n", "data: [DONE]\n\n"]);
    render(<Ask />);

    fireEvent.change(screen.getByPlaceholderText(/deine frage/i), {
      target: { value: "Frage" },
    });
    fireEvent.click(screen.getByRole("button", { name: /fragen/i }));

    await waitFor(() =>
      expect(screen.getByText(/\[error\] kaputt/i)).toBeInTheDocument(),
    );
  });

  it("shows an error on HTTP failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500, body: null }),
    );
    render(<Ask />);

    fireEvent.change(screen.getByPlaceholderText(/deine frage/i), {
      target: { value: "Frage" },
    });
    fireEvent.click(screen.getByRole("button", { name: /fragen/i }));

    await waitFor(() =>
      expect(screen.getByText(/http 500/i)).toBeInTheDocument(),
    );
  });
});
