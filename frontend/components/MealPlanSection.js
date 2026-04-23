import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection";
import styles from "../styles/MealPlanSection.module.css";

const DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"];
const DAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

function getMonday(d) {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  date.setDate(diff);
  date.setHours(0, 0, 0, 0);
  return date;
}

function toISODate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function formatWeekLabel(isoDate) {
  const d = new Date(isoDate + "T00:00:00");
  return d.toLocaleDateString("es-CL", { day: "numeric", month: "short" });
}

export default function MealPlanSection({ plan: initial, recetas }) {
  const [plan, setPlan] = useState(initial || { plan_id: null, week_start: toISODate(getMonday(new Date())), slots: ["almuerzo", "cena"], entries: [] });
  const [loading, setLoading] = useState(false);
  const [newSlot, setNewSlot] = useState("");
  const [addingSlot, setAddingSlot] = useState(false);
  const [shopping, setShopping] = useState(null);

  const recipeOptions = recetas || [];

  function getEntry(day, slot) {
    return plan.entries.find(e => e.day_of_week === day && e.slot_name === slot);
  }

  async function fetchWeek(weekStart) {
    setLoading(true);
    const res = await fetch(`/api/dashboard/meal-plan?week=${weekStart}`);
    if (res.ok) {
      const data = await res.json();
      setPlan(data);
    }
    setLoading(false);
  }

  function prevWeek() {
    const d = new Date(plan.week_start + "T00:00:00");
    d.setDate(d.getDate() - 7);
    fetchWeek(toISODate(d));
  }

  function nextWeek() {
    const d = new Date(plan.week_start + "T00:00:00");
    d.setDate(d.getDate() + 7);
    fetchWeek(toISODate(d));
  }

  async function handleCellChange(day, slot, recipeId) {
    const snapshot = plan;
    const entry = getEntry(day, slot);
    const recipeObj = recipeOptions.find(r => r.id === recipeId);

    setPlan(prev => {
      const filtered = prev.entries.filter(
        e => !(e.day_of_week === day && e.slot_name === slot)
      );
      if (!recipeId) return { ...prev, entries: filtered };
      return {
        ...prev,
        entries: [...filtered, {
          id: entry?.id || null,
          day_of_week: day,
          slot_name: slot,
          recipe_id: recipeId,
          recipe_name: recipeObj?.name || "",
        }],
      };
    });

    const res = await fetch("/api/dashboard/meal-plan/entries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        week_start: plan.week_start,
        day_of_week: day,
        slot_name: slot,
        recipe_id: recipeId || null,
      }),
    });
    if (!res.ok) setPlan(snapshot);
  }

  async function handleAddSlot(e) {
    e.preventDefault();
    const name = newSlot.trim();
    if (!name || plan.slots.includes(name)) return;
    const newSlots = [...plan.slots, name];
    const snapshot = plan;
    setPlan(prev => ({ ...prev, slots: newSlots }));
    setNewSlot("");
    setAddingSlot(false);

    const res = await fetch(`/api/dashboard/meal-plan/${plan.plan_id}/slots`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slots: newSlots }),
    });
    if (!res.ok) setPlan(snapshot);
  }

  async function handleDeleteSlot(slot) {
    const newSlots = plan.slots.filter(s => s !== slot);
    const snapshot = plan;
    setPlan(prev => ({
      ...prev,
      slots: newSlots,
      entries: prev.entries.filter(e => e.slot_name !== slot),
    }));

    const res = await fetch(`/api/dashboard/meal-plan/${plan.plan_id}/slots`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slots: newSlots }),
    });
    if (!res.ok) setPlan(snapshot);
  }

  async function handleGenerateShopping() {
    setShopping({ loading: true });
    const res = await fetch(`/api/dashboard/meal-plan/${plan.plan_id}/shopping`, {
      method: "POST",
    });
    if (!res.ok) { setShopping(null); return; }
    const data = await res.json();
    setShopping(data);
  }

  async function handleConfirmAdd(item) {
    const res = await fetch("/api/dashboard/shopping-list", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item, source: "meal_plan" }),
    });
    if (res.ok) {
      setShopping(prev => ({
        ...prev,
        confirm: prev.confirm.filter(c => c.item !== item),
        added: [...(prev.added || []), { item }],
      }));
    }
  }

  const hasPlannedMeals = plan.entries.some(e => e.recipe_id);

  return (
    <CollapsibleSection
      title="Plan de comidas"
      description="Planifica tus comidas de la semana y genera tu lista de compras automáticamente."
      defaultOpen={false}
    >
      <div className={styles.weekNav}>
        <button className={styles.navBtn} onClick={prevWeek} disabled={loading}>‹</button>
        <span className={styles.weekLabel}>
          Semana del {formatWeekLabel(plan.week_start)}
        </span>
        <button className={styles.navBtn} onClick={nextWeek} disabled={loading}>›</button>
      </div>

      {loading ? (
        <p className={styles.loading}>Cargando…</p>
      ) : (
        <div className={styles.gridWrapper}>
          <table className={styles.grid}>
            <thead>
              <tr>
                <th className={styles.slotHeader}></th>
                {DAY_LABELS.map(d => (
                  <th key={d} className={styles.dayHeader}>{d}</th>
                ))}
                <th></th>
              </tr>
            </thead>
            <tbody>
              {plan.slots.map(slot => (
                <tr key={slot}>
                  <td className={styles.slotName}>{slot}</td>
                  {DAYS.map(day => {
                    const entry = getEntry(day, slot);
                    return (
                      <td key={day} className={styles.cell}>
                        <select
                          className={styles.recipeSelect}
                          value={entry?.recipe_id || ""}
                          onChange={e => handleCellChange(day, slot, e.target.value || null)}
                        >
                          <option value="">—</option>
                          {recipeOptions.map(r => (
                            <option key={r.id} value={r.id}>{r.name}</option>
                          ))}
                        </select>
                      </td>
                    );
                  })}
                  <td>
                    <button
                      className={styles.deleteBtn}
                      onClick={() => handleDeleteSlot(slot)}
                      title="Eliminar fila"
                    >×</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className={styles.actions}>
        {addingSlot ? (
          <form className={styles.addSlotForm} onSubmit={handleAddSlot}>
            <input
              className={styles.slotInput}
              placeholder="nombre del horario"
              value={newSlot}
              onChange={e => setNewSlot(e.target.value)}
              autoFocus
            />
            <button className={styles.addBtn} type="submit">+</button>
            <button className={styles.cancelBtn} type="button" onClick={() => { setAddingSlot(false); setNewSlot(""); }}>×</button>
          </form>
        ) : (
          <button className={styles.addSlotBtn} onClick={() => setAddingSlot(true)}>
            + Agregar horario
          </button>
        )}

        <button
          className={styles.generateBtn}
          onClick={handleGenerateShopping}
          disabled={!hasPlannedMeals || shopping?.loading}
        >
          Generar lista de compras
        </button>
      </div>

      {shopping && !shopping.loading && (
        <div className={styles.shoppingResult}>
          {shopping.added?.length > 0 && (
            <div className={styles.addedMsg}>
              <p>✓ {shopping.added.length} ingrediente{shopping.added.length !== 1 ? "s" : ""} agregado{shopping.added.length !== 1 ? "s" : ""} a tu lista:</p>
              <ol className={styles.addedList}>
                {shopping.added.map((i, idx) => (
                  <li key={idx}>{i.item}</li>
                ))}
              </ol>
            </div>
          )}
          {shopping.confirm?.length > 0 && (
            <div className={styles.confirmList}>
              <p className={styles.confirmTitle}>Ya tienes en casa — ¿agregar a la lista?</p>
              {shopping.confirm.map(c => (
                <div key={c.item} className={styles.confirmRow}>
                  <span>{c.item} <span className={styles.qty}>({c.current_quantity} disponible{c.current_quantity !== 1 ? "s" : ""})</span></span>
                  <button className={styles.confirmBtn} onClick={() => handleConfirmAdd(c.item)}>+ Agregar</button>
                </div>
              ))}
            </div>
          )}
          {shopping.added?.length === 0 && shopping.confirm?.length === 0 && (
            <p className={styles.addedMsg}>Todo lo necesario ya está en tu lista o despensa.</p>
          )}
        </div>
      )}
    </CollapsibleSection>
  );
}
