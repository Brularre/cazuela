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
});
