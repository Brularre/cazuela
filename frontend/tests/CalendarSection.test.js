import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CalendarSection from "../components/CalendarSection.jsx";

const future = new Date(Date.now() + 3600 * 1000).toISOString();

function open() {
  fireEvent.click(screen.getByRole("button", { name: /Calendario/i }));
}

describe("CalendarSection", () => {
  it("renders empty state when no events after opening", () => {
    render(<CalendarSection eventos={[]} icalUrl={null} />);
    open();
    expect(screen.getByText("No tienes eventos próximos.")).toBeInTheDocument();
  });

  it("renders event title after opening", () => {
    render(
      <CalendarSection
        eventos={[{ id: "1", title: "Dentista", starts_at: future, category: "salud" }]}
        icalUrl={null}
      />
    );
    open();
    expect(screen.getByText("Dentista")).toBeInTheDocument();
  });

  it("renders iCal link when icalUrl is provided", () => {
    render(<CalendarSection eventos={[]} icalUrl="https://example.com/calendar/tok.ics" />);
    open();
    expect(screen.getByRole("link", { name: /https/i })).toBeInTheDocument();
  });

  it("removes event optimistically on delete", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    render(
      <CalendarSection
        eventos={[{ id: "1", title: "Reunión", starts_at: future, category: "trabajo" }]}
        icalUrl={null}
      />
    );
    open();
    fireEvent.click(screen.getByTitle("Eliminar"));
    await waitFor(() =>
      expect(screen.queryByText("Reunión")).not.toBeInTheDocument()
    );
  });

  it("renders reminder button for each event", () => {
    render(
      <CalendarSection
        eventos={[{ id: "1", title: "Dentista", starts_at: future, category: "salud", remind_at: null }]}
        icalUrl={null}
      />
    );
    open();
    expect(screen.getByRole("button", { name: "Recordatorio" })).toBeInTheDocument();
  });

  it("shows reminder time in button when remind_at is set", () => {
    const remindAt = new Date(Date.now() + 1800 * 1000).toISOString();
    render(
      <CalendarSection
        eventos={[{ id: "1", title: "Dentista", starts_at: future, category: "salud", remind_at: remindAt }]}
        icalUrl={null}
      />
    );
    open();
    const btn = screen.getByRole("button", { name: "Recordatorio" });
    expect(btn.textContent).toContain("⏰");
  });

  it("opens reminder editor on button click", () => {
    render(
      <CalendarSection
        eventos={[{ id: "1", title: "Dentista", starts_at: future, category: "salud", remind_at: null }]}
        icalUrl={null}
      />
    );
    open();
    fireEvent.click(screen.getByRole("button", { name: "Recordatorio" }));
    expect(screen.getByLabelText("Hora del recordatorio")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar" })).toBeInTheDocument();
  });

  it("calls PATCH reminder endpoint on save", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    render(
      <CalendarSection
        eventos={[{ id: "e-1", title: "Dentista", starts_at: future, category: "salud", remind_at: null }]}
        icalUrl={null}
      />
    );
    open();
    fireEvent.click(screen.getByRole("button", { name: "Recordatorio" }));
    fireEvent.change(screen.getByLabelText("Hora del recordatorio"), {
      target: { value: "2025-06-17T09:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/dashboard/events/e-1/reminder",
        expect.objectContaining({ method: "PATCH" })
      )
    );
  });
});
