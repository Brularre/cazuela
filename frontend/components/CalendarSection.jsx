import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection.jsx";
import styles from "./CalendarSection.module.css";

const CATEGORY_LABELS = {
  trabajo: "Trabajo",
  personal: "Personal",
  salud: "Salud",
  social: "Social",
  viajes: "Viajes",
  otro: "Otro",
};

function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleString("es-CL", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function CalendarSection({ eventos, icalUrl }) {
  const [items, setItems] = useState(eventos || []);
  const [title, setTitle] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [category, setCategory] = useState("otro");
  const [adding, setAdding] = useState(false);

  async function remove(id) {
    const snapshot = items;
    setItems((prev) => prev.filter((e) => e.id !== id));
    const res = await fetch(`/api/dashboard/events/${id}`, { method: "DELETE" });
    if (!res.ok) setItems(snapshot);
  }

  async function add(e) {
    e.preventDefault();
    if (!title.trim() || !startsAt) return;
    setAdding(true);
    const res = await fetch("/api/dashboard/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title.trim(),
        starts_at: new Date(startsAt).toISOString(),
        category,
      }),
    });
    if (res.ok) {
      const row = await res.json();
      setItems((prev) => [...prev, row].sort((a, b) => a.starts_at.localeCompare(b.starts_at)));
      setTitle("");
      setStartsAt("");
      setCategory("otro");
    }
    setAdding(false);
  }

  return (
    <CollapsibleSection
      title="Calendario"
      description="Tus próximos eventos."
    >
      {items.length === 0 && <p className={styles.empty}>No tienes eventos próximos.</p>}
      <ul className={styles.list}>
        {items.map((ev) => (
          <li key={ev.id} className={styles.item}>
            <span className={styles.cat}>{CATEGORY_LABELS[ev.category] || ev.category}</span>
            <span className={styles.evTitle}>{ev.title}</span>
            <span className={styles.date}>{fmtDate(ev.starts_at)}</span>
            <button className={styles.delete} onClick={() => remove(ev.id)} title="Eliminar">×</button>
          </li>
        ))}
      </ul>

      <form onSubmit={add} className={styles.addForm}>
        <input
          className={styles.input}
          placeholder="Título del evento…"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <input
          className={styles.input}
          type="datetime-local"
          value={startsAt}
          onChange={(e) => setStartsAt(e.target.value)}
          required
        />
        <select
          className={styles.select}
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <button className={styles.addBtn} type="submit" disabled={adding}>
          {adding ? "…" : "Agregar"}
        </button>
      </form>

      {icalUrl && (
        <p className={styles.icalNote}>
          Suscripción iCal:{" "}
          <a className={styles.icalLink} href={icalUrl} target="_blank" rel="noreferrer">
            {icalUrl}
          </a>
        </p>
      )}
    </CollapsibleSection>
  );
}
