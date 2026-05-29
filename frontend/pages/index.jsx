import { useState } from "react";
import { useRouter } from "next/router";
import Header from "../components/Header.jsx";
import SettingsModal from "../components/SettingsModal.jsx";
import ExpensesSection from "../components/ExpensesSection.jsx";
import TodosSection from "../components/TodosSection.jsx";
import WaitingSection from "../components/WaitingSection.jsx";
import ShoppingSection from "../components/ShoppingSection.jsx";
import PantrySection from "../components/PantrySection.jsx";
import RecipesSection from "../components/RecipesSection.jsx";
import MealPlanSection from "../components/MealPlanSection.jsx";
import CalendarSection from "../components/CalendarSection.jsx";
import ModulesSection from "../components/ModulesSection.jsx";
import styles from "../styles/dashboard.module.css";

export default function Dashboard({ data }) {
  const router = useRouter();
  const [showSettings, setShowSettings] = useState(false);

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    router.push("/login");
  }

  return (
    <>
      <Header onLogout={handleLogout} onSettings={() => setShowSettings(true)} />
      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
      <main className={styles.main}>
        {(data.modulos?.dinero !== false) && <ExpensesSection gastos={data.gastos} />}
        {(data.modulos?.comida !== false) && <ShoppingSection compras={data.compras} />}
        {(data.modulos?.tiempo !== false) && <TodosSection pendientes={data.pendientes} />}
        {(data.modulos?.tiempo !== false) && <WaitingSection esperando={data.esperando} />}
        {(data.modulos?.comida !== false) && <PantrySection despensa={data.despensa} />}
        {(data.modulos?.calendario !== false) && <CalendarSection eventos={data.eventos} icalUrl={data.ical_url} />}
        {(data.modulos?.comida !== false) && <RecipesSection recetas={data.recetas} />}
        {(data.modulos?.comida !== false) && <MealPlanSection plan={data.plan} recetas={data.recetas} />}
        <ModulesSection modulos={data.modulos} />
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
  data.recetas = data.recetas ?? [];
  data.plan = data.plan ?? null;
  data.eventos = data.eventos ?? [];
  data.modulos = data.modulos ?? {};

  return { props: { data } };
}
