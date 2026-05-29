import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ModulesSection from "../components/ModulesSection.jsx";

const defaultModulos = {
  dinero: true,
  tiempo: true,
  comida: true,
  calendario: true,
  recordatorios: true,
};

function open() {
  fireEvent.click(screen.getByRole("button", { name: /Módulos/i }));
}

describe("ModulesSection", () => {
  it("renders all module labels after opening", () => {
    render(<ModulesSection modulos={defaultModulos} />);
    open();
    expect(screen.getByText("Dinero")).toBeInTheDocument();
    expect(screen.getByText("Tiempo")).toBeInTheDocument();
    expect(screen.getByText("Comida")).toBeInTheDocument();
    expect(screen.getByText("Calendario")).toBeInTheDocument();
    expect(screen.getByText("Recordatorios")).toBeInTheDocument();
  });

  it("shows Activo for enabled modules", () => {
    render(<ModulesSection modulos={defaultModulos} />);
    open();
    const buttons = screen.getAllByText("Activo");
    expect(buttons).toHaveLength(5);
  });

  it("shows Inactivo for disabled module", () => {
    render(<ModulesSection modulos={{ ...defaultModulos, comida: false }} />);
    open();
    expect(screen.getByText("Inactivo")).toBeInTheDocument();
  });

  it("toggles module and calls PATCH on click", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    render(<ModulesSection modulos={defaultModulos} />);
    open();
    const btns = screen.getAllByText("Activo");
    fireEvent.click(btns[0]);
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/modules/"),
        expect.objectContaining({ method: "PATCH" })
      )
    );
  });
});
