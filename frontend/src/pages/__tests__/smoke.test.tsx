import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import Dashboard from "../Dashboard";

function renderWithProviders(ui: ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Dashboard", () => {
  it("renders the page header and primary action", () => {
    renderWithProviders(<Dashboard />);
    expect(screen.getByRole("heading", { level: 1, name: /Dashboard/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Import data/i })).toBeDefined();
  });
});
