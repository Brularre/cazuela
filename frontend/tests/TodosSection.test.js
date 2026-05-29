import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import TodosSection from "../components/TodosSection.jsx";

describe("TodosSection", () => {
  it("renders empty state message when no todos", () => {
    render(<TodosSection pendientes={{ hoy: [], semana: [], mes: [] }} />);
    expect(screen.getByText("Todo al día.")).toBeInTheDocument();
  });

  it("renders todos grouped by bucket", () => {
    render(
      <TodosSection
        pendientes={{
          hoy: [{ id: "1", task: "llamar al banco" }],
          semana: [{ id: "2", task: "comprar pan" }],
          mes: [],
        }}
      />
    );
    expect(screen.getByText("Llamar al banco")).toBeInTheDocument();
    expect(screen.getByText("Comprar pan")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hoy" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Esta semana" })).toBeInTheDocument();
  });

  it("renders the add task form", () => {
    render(<TodosSection pendientes={{ hoy: [], semana: [], mes: [] }} />);
    expect(screen.getByPlaceholderText("Nueva tarea…")).toBeInTheDocument();
  });

  it("adds a new todo optimistically on successful POST", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "99", task: "nueva tarea", priority: "hoy" }),
    });
    render(<TodosSection pendientes={{ hoy: [], semana: [], mes: [] }} />);

    fireEvent.change(screen.getByPlaceholderText("Nueva tarea…"), {
      target: { value: "nueva tarea" },
    });
    fireEvent.submit(screen.getByPlaceholderText("Nueva tarea…").closest("form"));

    await waitFor(() =>
      expect(screen.getByText("Nueva tarea")).toBeInTheDocument()
    );
  });
});
