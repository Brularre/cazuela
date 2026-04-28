import { useState } from "react";
import { useRouter } from "next/router";
import Header from "../components/Header";
import SettingsModal from "../components/SettingsModal";
import ExpensesSection from "../components/ExpensesSection";
import TodosSection from "../components/TodosSection";
import WaitingSection from "../components/WaitingSection";
import ShoppingSection from "../components/ShoppingSection";
import PantrySection from "../components/PantrySection";
import RecipesSection from "../components/RecipesSection";
import MealPlanSection from "../components/MealPlanSection";
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
        <ExpensesSection gastos={data.gastos} />
        <ShoppingSection compras={data.compras} />
        <TodosSection pendientes={data.pendientes} />
        <WaitingSection esperando={data.esperando} />
        <PantrySection despensa={data.despensa} />
        <RecipesSection recetas={data.recetas} />
        <MealPlanSection plan={data.plan} recetas={data.recetas} />
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

  return { props: { data } };
}
