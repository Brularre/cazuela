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

  it("renders reminder button for each todo", () => {
    render(
      <TodosSection
        pendientes={{
          hoy: [{ id: "1", task: "llamar al banco", remind_at: null }],
          semana: [],
          mes: [],
        }}
      />
    );
    expect(screen.getByRole("button", { name: "Recordatorio" })).toBeInTheDocument();
  });

  it("shows reminder time in button when remind_at is set", () => {
    const future = new Date(Date.now() + 3600 * 1000).toISOString();
    render(
      <TodosSection
        pendientes={{
          hoy: [{ id: "1", task: "llamar al banco", remind_at: future }],
          semana: [],
          mes: [],
        }}
      />
    );
    const btn = screen.getByRole("button", { name: "Recordatorio" });
    expect(btn.textContent).toContain("⏰");
  });

  it("opens reminder editor on button click", () => {
    render(
      <TodosSection
        pendientes={{
          hoy: [{ id: "1", task: "tarea", remind_at: null }],
          semana: [],
          mes: [],
        }}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "Recordatorio" }));
    expect(screen.getByLabelText("Hora del recordatorio")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar" })).toBeInTheDocument();
  });

  it("calls PATCH reminder endpoint on save", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    const future = new Date(Date.now() + 3600 * 1000).toISOString();
    render(
      <TodosSection
        pendientes={{
          hoy: [{ id: "t-1", task: "tarea", remind_at: null }],
          semana: [],
          mes: [],
        }}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "Recordatorio" }));
    fireEvent.change(screen.getByLabelText("Hora del recordatorio"), {
      target: { value: "2025-06-17T10:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/dashboard/todos/t-1/reminder",
        expect.objectContaining({ method: "PATCH" })
      )
    );
  });
});
