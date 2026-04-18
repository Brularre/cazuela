import { useRouter } from "next/router";
import Header from "../components/Header";
import GastosSection from "../components/GastosSection";
import PendientesSection from "../components/PendientesSection";
import EsperandoSection from "../components/EsperandoSection";
import ShoppingSection from "../components/ShoppingSection";
import DespeSection from "../components/DespeSection";
import PlaceholderSection from "../components/PlaceholderSection";
import styles from "../styles/dashboard.module.css";

export default function Dashboard({ data }) {
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    router.push("/login");
  }

  return (
    <>
      <Header onLogout={handleLogout} />
      <main className={styles.main}>
        <GastosSection gastos={data.gastos} />
        <PendientesSection pendientes={data.pendientes} />
        <ShoppingSection compras={data.compras} />
        <EsperandoSection esperando={data.esperando} />
        <DespeSection despensa={data.despensa} />
        <PlaceholderSection
          title="Calendario"
          description="Integración con Google Calendar próximamente."
        />
      </main>
    </>
  );
}

export async function getServerSideProps(context) {
  const session = context.req.cookies?.session;

  if (!session) {
    return { redirect: { destination: "/login", permanent: false } };
  }

  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

  let data;
  try {
    const res = await fetch(`${backendUrl}/dashboard`, {
      headers: { Cookie: `session=${session}` },
    });

    if (res.status === 401) {
      return { redirect: { destination: "/login", permanent: false } };
    }

    data = await res.json();
  } catch {
    data = {
      gastos: null,
      pendientes: { hoy: [], semana: [], mes: [] },
      esperando: [],
      compras: [],
      despensa: { cocina: [], baño: [], otros: [] },
    };
  }

  data.compras = data.compras ?? [];
  data.despensa = data.despensa ?? { cocina: [], baño: [], otros: [] };

  return { props: { data } };
}
