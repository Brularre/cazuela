import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection";
import AddItemForm from "./AddItemForm";
import styles from "./TodosSection.module.css";

const BUCKET_LABELS = { hoy: "Hoy", semana: "Esta semana", mes: "Este mes" };

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
