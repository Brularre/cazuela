import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection";
import styles from "../styles/ShoppingSection.module.css";

export default function ShoppingSection({ compras: initial }) {
  const [items, setItems] = useState(initial || []);

  async function handleRestock(id) {
    setItems(prev => prev.filter(i => i.id !== id));
    await fetch(`/api/dashboard/pantry/${id}/restock`, { method: "PATCH" });
  }

  async function handleCheck(id) {
    setItems(prev => prev.filter(i => i.id !== id));
    await fetch(`/api/dashboard/shopping/${id}/check`, { method: "PATCH" });
  }

  const pantryItems = items.filter(i => i.source === "pantry");

  async function handleRestockAll() {
    setItems(prev => prev.filter(i => i.source !== "pantry"));
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
                <span className={i.source === "lista" ? styles.nameManual : styles.name}>
                  {i.item}
                </span>
                {i.source === "pantry" && (
                  <span className={styles.qty}>{i.current_quantity}/{i.desired_quantity}</span>
                )}
                <button
                  className={i.source === "lista" ? styles.btnGhost : styles.btn}
                  onClick={() => i.source === "lista" ? handleCheck(i.id) : handleRestock(i.id)}
                >
                  Compré
                </button>
              </li>
            ))}
          </ul>
          {pantryItems.length > 0 && (
            <button className={styles.btnAll} onClick={handleRestockAll}>
              Compré todo (despensa)
            </button>
          )}
        </>
      )}
    </CollapsibleSection>
  );
}
