import { render, screen, fireEvent } from "@testing-library/react";
import Login from "../pages/login.jsx";

describe("Login", () => {
  it("renders step 1 with phone input and submit button", () => {
    render(<Login />);
    expect(screen.getByText("Cazuela")).toBeInTheDocument();
    expect(screen.getByText("Ingresa tu número de WhatsApp")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar código" })).toBeInTheDocument();
  });

  it("advances to step 2 after successful OTP request", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    render(<Login />);

    fireEvent.change(screen.getByPlaceholderText("+56912345678"), {
      target: { value: "+15555550100" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enviar código" }));

    expect(await screen.findByText("Ingresa el código enviado a WhatsApp")).toBeInTheDocument();
  });

  it("shows error on failed OTP request", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false });
    render(<Login />);

    fireEvent.change(screen.getByPlaceholderText("+56912345678"), {
      target: { value: "+15555550100" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enviar código" }));

    expect(
      await screen.findByText("Error al enviar el código. Intenta nuevamente.")
    ).toBeInTheDocument();
  });
});
