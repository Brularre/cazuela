import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection";
import styles from "./TodosSection.module.css";

const BUCKET_LABELS = { hoy: "Hoy", semana: "Esta semana", mes: "Este mes" };

export default function TodosSection({ pendientes }) {
  const [items, setItems] = useState(pendientes || { hoy: [], semana: [], mes: [] });

  async function complete(id) {
    setItems((prev) => {
      const next = {};
      for (const bucket of ["hoy", "semana", "mes"]) {
        next[bucket] = (prev[bucket] || []).filter((t) => t.id !== id);
      }
      return next;
    });
    await fetch(`/api/dashboard/todos/${id}/complete`, { method: "PATCH" });
  }

  const total = ["hoy", "semana", "mes"].reduce(
    (n, b) => n + (items[b] || []).length, 0
  );

  return (
    <CollapsibleSection title="Pendientes" defaultOpen>
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
                  <button
                    className={styles.complete}
                    onClick={() => complete(todo.id)}
                  >
                    ✓
                  </button>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </CollapsibleSection>
  );
}
