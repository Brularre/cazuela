import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection";
import styles from "./EsperandoSection.module.css";

function daysAgo(isoDate) {
  const ms = Date.now() - new Date(isoDate).getTime();
  const days = Math.floor(ms / 86400000);
  if (days === 0) return "hoy";
  if (days === 1) return "hace 1 día";
  return `hace ${days} días`;
}

export default function EsperandoSection({ esperando }) {
  const [items, setItems] = useState(esperando || []);

  async function resolve(id) {
    setItems((prev) => prev.filter((i) => i.id !== id));
    await fetch(`/api/dashboard/waiting_on/${id}/resolve`, { method: "PATCH" });
  }

  return (
    <CollapsibleSection title="Esperando">
      {items.length === 0 && (
        <p className={styles.empty}>Nada pendiente de otros.</p>
      )}
      <ul className={styles.list}>
        {items.map((item) => (
          <li key={item.id} className={styles.item}>
            <div className={styles.info}>
              <span className={styles.description}>{item.description.charAt(0).toUpperCase() + item.description.slice(1)}</span>
              <span className={styles.age}>{daysAgo(item.created_at)}</span>
            </div>
            <button
              className={styles.resolve}
              onClick={() => resolve(item.id)}
            >
              Llegó
            </button>
          </li>
        ))}
      </ul>
    </CollapsibleSection>
  );
}
