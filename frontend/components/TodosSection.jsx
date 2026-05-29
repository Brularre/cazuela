import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection.jsx";
import AddItemForm from "./AddItemForm.jsx";
import styles from "./TodosSection.module.css";

const BUCKET_LABELS = { hoy: "Hoy", semana: "Esta semana", mes: "Este mes" };

function fmtReminder(iso) {
  if (!iso) return null;
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

function TodoReminderControl({ todoId, remindAt, onUpdate }) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(toDatetimeLocal(remindAt));
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    const iso = value ? new Date(value).toISOString() : null;
    const res = await fetch(`/api/dashboard/todos/${todoId}/reminder`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ remind_at: iso }),
    });
    if (res.ok) {
      onUpdate(todoId, iso);
      setOpen(false);
    }
    setSaving(false);
  }

  async function clear() {
    setSaving(true);
    const res = await fetch(`/api/dashboard/todos/${todoId}/reminder`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ remind_at: null }),
    });
    if (res.ok) {
      onUpdate(todoId, null);
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
        title={remindAt ? `Recordatorio: ${fmtReminder(remindAt)}` : "Agregar recordatorio"}
        aria-label="Recordatorio"
      >
        {remindAt ? `⏰ ${fmtReminder(remindAt)}` : "⏰"}
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

export default function TodosSection({ pendientes }) {
  const [items, setItems] = useState(pendientes || { hoy: [], semana: [], mes: [] });
  const [newTask, setNewTask] = useState("");
  const [newPriority, setNewPriority] = useState("semana");
  const [adding, setAdding] = useState(false);

  async function optimisticRemove(id, url, method = "PATCH") {
    const snapshot = items;
    setItems((prev) => {
      const next = {};
      for (const bucket of ["hoy", "semana", "mes"]) {
        next[bucket] = (prev[bucket] || []).filter((t) => t.id !== id);
      }
      return next;
    });
    const res = await fetch(url, { method });
    if (!res.ok) setItems(snapshot);
  }

  const complete = (id) => optimisticRemove(id, `/api/dashboard/todos/${id}/complete`);
  const remove = (id) => optimisticRemove(id, `/api/dashboard/todos/${id}`, "DELETE");

  function updateReminder(id, remindAt) {
    setItems((prev) => {
      const next = {};
      for (const bucket of ["hoy", "semana", "mes"]) {
        next[bucket] = (prev[bucket] || []).map((t) =>
          t.id === id ? { ...t, remind_at: remindAt } : t
        );
      }
      return next;
    });
  }

  async function add(e) {
    e.preventDefault();
    const task = newTask.trim();
    if (!task) return;
    setAdding(true);
    const res = await fetch("/api/dashboard/todos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task, priority: newPriority }),
    });
    if (res.ok) {
      const row = await res.json();
      setItems((prev) => ({
        ...prev,
        [row.priority]: [...(prev[row.priority] || []), row],
      }));
      setNewTask("");
    }
    setAdding(false);
  }

  const total = ["hoy", "semana", "mes"].reduce(
    (n, b) => n + (items[b] || []).length, 0
  );

  return (
    <CollapsibleSection
      title="Pendientes"
      description="Agrega tareas desde aquí o desde WhatsApp con 'pendiente llamar al banco'."
      defaultOpen
    >
      {total === 0 && <p className={styles.empty}>Todo al día.</p>}
      {["hoy", "semana", "mes"].map((bucket) => {
        const list = items[bucket] || [];
        if (list.length === 0) return null;
        return (
          <div key={bucket} className={styles.bucket}>
            <h3 className={styles.bucketLabel}>{BUCKET_LABELS[bucket]}</h3>
            <ul className={styles.list}>
              {list.map((todo) => (
                <li key={todo.id} className={styles.item}>
                  <span className={styles.task}>{todo.task.charAt(0).toUpperCase() + todo.task.slice(1)}</span>
                  <TodoReminderControl
                    todoId={todo.id}
                    remindAt={todo.remind_at}
                    onUpdate={updateReminder}
                  />
                  <button className={styles.complete} onClick={() => complete(todo.id)} title="Completar">✓</button>
                  <button className={styles.delete} onClick={() => remove(todo.id)} title="Eliminar">×</button>
                </li>
              ))}
            </ul>
          </div>
        );
      })}

      <AddItemForm
        value={newTask}
        onChange={(e) => setNewTask(e.target.value)}
        onSubmit={add}
        placeholder="Nueva tarea…"
        submitting={adding}
      >
        <select
          className={styles.addSelect}
          value={newPriority}
          onChange={(e) => setNewPriority(e.target.value)}
        >
          <option value="hoy">Hoy</option>
          <option value="semana">Semana</option>
          <option value="mes">Mes</option>
        </select>
      </AddItemForm>
    </CollapsibleSection>
  );
}
