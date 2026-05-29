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

function toDatetimeLocal(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function EventReminderControl({ eventId, remindAt, onUpdate }) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(toDatetimeLocal(remindAt));
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    const iso = value ? new Date(value).toISOString() : null;
    const res = await fetch(`/api/dashboard/events/${eventId}/reminder`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ remind_at: iso }),
    });
    if (res.ok) {
      onUpdate(eventId, iso);
      setOpen(false);
    }
    setSaving(false);
  }

  async function clear() {
    setSaving(true);
    const res = await fetch(`/api/dashboard/events/${eventId}/reminder`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ remind_at: null }),
    });
    if (res.ok) {
      onUpdate(eventId, null);
      setValue("");
      setOpen(false);
    }
    setSaving(false);
  }

  return (
    <>
      <button
        className={styles.reminderBtn}
        onClick={() => setOpen((o) => !o)}
        title={remindAt ? `Recordatorio: ${fmtDate(remindAt)}` : "Agregar recordatorio"}
        aria-label="Recordatorio"
      >
        {remindAt ? `⏰ ${fmtDate(remindAt)}` : "⏰"}
      </button>
      {open && (
        <div className={styles.reminderRow}>
          <input
            className={styles.reminderInput}
            type="datetime-local"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            aria-label="Hora del recordatorio"
          />
          <button className={styles.reminderSave} onClick={save} disabled={saving}>
            {saving ? "…" : "Guardar"}
          </button>
          {remindAt && (
            <button className={styles.reminderClear} onClick={clear} disabled={saving}>
              Borrar
            </button>
          )}
        </div>
      )}
    </>
  );
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

  function updateReminder(id, remindAt) {
    setItems((prev) =>
      prev.map((ev) => (ev.id === id ? { ...ev, remind_at: remindAt } : ev))
    );
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
            <EventReminderControl
              eventId={ev.id}
              remindAt={ev.remind_at}
              onUpdate={updateReminder}
            />
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
