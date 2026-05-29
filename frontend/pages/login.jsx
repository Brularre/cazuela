import { useState } from "react";
import { useRouter } from "next/router";
import styles from "../styles/login.module.css";

const waNumber = process.env.NEXT_PUBLIC_WA_NUMBER;
const waLink = waNumber ? `https://wa.me/${waNumber}?text=hola` : null;

export default function Login() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleRequestOtp(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/auth/request-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
      });
      if (res.ok) {
        setStep(2);
      } else {
        setError("Error al enviar el código. Intenta nuevamente.");
      }
    } catch {
      setError("Error de conexión. Intenta nuevamente.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/auth/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, code }),
      });
      if (res.ok) {
        router.push("/");
      } else {
        setError("Código incorrecto o expirado.");
      }
    } catch {
      setError("Error de conexión. Intenta nuevamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <img src="/logo.webp" alt="Cazuela" className={styles.logo} />
        <h1 className={styles.title}>Cazuela</h1>
        {step === 1 ? (
          <form onSubmit={handleRequestOtp}>
            <p className={styles.subtitle}>Ingresa tu número de WhatsApp</p>
            <input
              className={styles.input}
              type="tel"
              placeholder="+56912345678"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
            {error && <p className={styles.error}>{error}</p>}
            <button className={styles.button} type="submit" disabled={loading}>
              {loading ? "Enviando..." : "Enviar código"}
            </button>
            {waLink && (
              <p className={styles.hint}>
                ¿Primera vez?{" "}
                <a href={waLink} target="_blank" rel="noreferrer" className={styles.waLink}>
                  Tu cuenta se crea cuando envías tu primer mensaje a Cazuela en WhatsApp
                </a>.
              </p>
            )}
          </form>
        ) : (
          <form onSubmit={handleVerifyOtp}>
            <p className={styles.subtitle}>Ingresa el código enviado a WhatsApp</p>
            <input
              className={styles.input}
              type="text"
              placeholder="123456"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={6}
              required
            />
            {error && <p className={styles.error}>{error}</p>}
            <button className={styles.button} type="submit" disabled={loading}>
              {loading ? "Verificando..." : "Ingresar"}
            </button>
            <button
              className={styles.back}
              type="button"
              onClick={() => { setStep(1); setError(""); }}
            >
              Volver
            </button>
            {waLink && (
              <p className={styles.hint}>
                ¿No llegó el código?{" "}
                <a href={waLink} target="_blank" rel="noreferrer" className={styles.waLink}>
                  Primero envía un mensaje a Cazuela
                </a>.
              </p>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
