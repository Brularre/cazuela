import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection";
import AddItemForm from "./AddItemForm";
import styles from "./WaitingSection.module.css";

function daysAgo(isoDate) {
  const ms = Date.now() - new Date(isoDate).getTime();
  const days = Math.floor(ms / 86400000);
  if (days === 0) return "hoy";
  if (days === 1) return "hace 1 día";
  return `hace ${days} días`;
}

export default function WaitingSection({ esperando }) {
  const [items, setItems] = useState(esperando || []);
  const [newDesc, setNewDesc] = useState("");
  const [adding, setAdding] = useState(false);

  async function optimisticRemove(id, url, method = "PATCH") {
    const snapshot = items;
    setItems((prev) => prev.filter((i) => i.id !== id));
    const res = await fetch(url, { method });
    if (!res.ok) setItems(snapshot);
  }

  const resolve = (id) => optimisticRemove(id, `/api/dashboard/waiting_on/${id}/resolve`);
  const remove = (id) => optimisticRemove(id, `/api/dashboard/waiting_on/${id}`, "DELETE");

  async function add(e) {
    e.preventDefault();
    const description = newDesc.trim();
    if (!description) return;
    setAdding(true);
    const res = await fetch("/api/dashboard/waiting_on", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description }),
    });
    if (res.ok) {
      const row = await res.json();
      setItems((prev) => [...prev, row]);
      setNewDesc("");
    }
    setAdding(false);
  }

  return (
    <CollapsibleSection
      title="Pendientes (de terceros)"
      description="Registra lo que estás esperando de otros. Ciérralos cuando lleguen tocando 'Llegó'."
    >
      {items.length === 0 ? (
        <p className={styles.empty}>Nada pendiente de otros.</p>
      ) : (
        <ul className={styles.list}>
          {items.map((item) => (
            <li key={item.id} className={styles.item}>
              <div className={styles.info}>
                <span className={styles.description}>{item.description.charAt(0).toUpperCase() + item.description.slice(1)}</span>
                <span className={styles.age}>{daysAgo(item.created_at)}</span>
              </div>
              <button className={styles.resolve} onClick={() => resolve(item.id)}>Llegó</button>
              <button className={styles.delete} onClick={() => remove(item.id)} title="Eliminar">×</button>
            </li>
          ))}
        </ul>
      )}
      <AddItemForm
        value={newDesc}
        onChange={(e) => setNewDesc(e.target.value)}
        onSubmit={add}
        placeholder="Esperando respuesta de…"
        submitting={adding}
      />
    </CollapsibleSection>
  );
}
