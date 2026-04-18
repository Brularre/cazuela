import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection";
import styles from "../styles/ShoppingSection.module.css";

export default function ShoppingSection({ compras: initial }) {
  const [items, setItems] = useState(initial || []);

  async function handleRestock(id) {
    setItems(prev => prev.filter(i => i.id !== id));
    await fetch(`/api/dashboard/pantry/${id}/restock`, { method: "PATCH" });
  }

  async function handleRestockAll() {
    setItems([]);
    await fetch("/api/dashboard/pantry/restock-all", { method: "PATCH" });
  }

  return (
    <CollapsibleSection title="Lista de compras" defaultOpen={true}>
      {items.length === 0 ? (
        <p className={styles.empty}>Todo está al día.</p>
      ) : (
        <>
          <ul className={styles.list}>
            {items.map(i => (
              <li key={i.id} className={styles.item}>
                <span className={styles.name}>{i.item}</span>
                <span className={styles.qty}>{i.current_quantity}/{i.desired_quantity}</span>
                <button className={styles.btn} onClick={() => handleRestock(i.id)}>
                  Compré
                </button>
              </li>
            ))}
          </ul>
          <button className={styles.btnAll} onClick={handleRestockAll}>
            Compré todo
          </button>
        </>
      )}
    </CollapsibleSection>
  );
}
