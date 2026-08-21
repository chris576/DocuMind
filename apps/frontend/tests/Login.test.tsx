import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Login from "../src/pages/Login";

// useNavigate wird gemockt, da der Login nur clientseitig navigiert.
const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

describe("Login", () => {
  it("renders the sign-in form", () => {
    render(<Login />);
    expect(screen.getByRole("heading", { name: /DMS-RAG/i })).toBeTruthy();
    expect(screen.getByPlaceholderText(/username/i)).toBeTruthy();
    expect(screen.getByPlaceholderText(/password/i)).toBeTruthy();
  });

  it("navigates to dashboard on submit", () => {
    render(<Login />);
    fireEvent.change(screen.getByPlaceholderText(/username/i), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByPlaceholderText(/password/i), {
      target: { value: "secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(mockNavigate).toHaveBeenCalledWith("/dashboard");
  });
});
