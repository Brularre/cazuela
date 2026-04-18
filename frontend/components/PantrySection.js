import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection";
import styles from "../styles/PantrySection.module.css";

const TABS = ["cocina", "baño", "otros"];
const TAB_LABELS = { cocina: "Cocina", baño: "Baño", otros: "Otros" };
const DESCRIPTIONS = {
  cocina: "Proteínas, vegetales, frutas, lácteos…",
  baño: "Medicamentos, cosméticos, desodorantes…",
  otros: "Comida de mascota, pilas, velas…",
};

export default function PantrySection({ despensa: initial }) {
  const [items, setItems] = useState(initial || { cocina: [], baño: [], otros: [] });
  const [activeTab, setActiveTab] = useState("cocina");
  const [newItem, setNewItem] = useState({ item: "", desired_quantity: 1 });
  const [editingId, setEditingId] = useState(null);
  const [editQty, setEditQty] = useState("");

  const tabItems = items[activeTab] || [];

  async function handleAdd(e) {
    e.preventDefault();
    if (!newItem.item.trim()) return;
    const body = { ...newItem, category: activeTab };
    const res = await fetch("/api/dashboard/pantry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return;
    const { id } = await res.json();
    setItems(prev => ({
      ...prev,
      [activeTab]: [...prev[activeTab], {
        id,
        item: newItem.item,
        desired_quantity: newItem.desired_quantity,
        current_quantity: newItem.desired_quantity,
      }],
    }));
    setNewItem({ item: "", desired_quantity: 1 });
  }

  async function handleDelete(id) {
    setItems(prev => ({
      ...prev,
      [activeTab]: prev[activeTab].filter(i => i.id !== id),
    }));
    await fetch(`/api/dashboard/pantry/${id}`, { method: "DELETE" });
  }

  function startEdit(id, qty) {
    setEditingId(id);
    setEditQty(String(qty));
  }

  async function commitEdit(id) {
    const qty = parseInt(editQty, 10);
    if (isNaN(qty) || qty < 1) { setEditingId(null); return; }
    setItems(prev => ({
      ...prev,
      [activeTab]: prev[activeTab].map(i =>
        i.id === id ? { ...i, desired_quantity: qty } : i
      ),
    }));
    setEditingId(null);
    await fetch(`/api/dashboard/pantry/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ desired_quantity: qty }),
    });
  }

  return (
    <CollapsibleSection title="Despensa" defaultOpen={false}>
      <div className={styles.tabs}>
        {TABS.map(tab => (
          <button
            key={tab}
            className={`${styles.tab} ${activeTab === tab ? styles.tabActive : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      <table className={styles.table}>
        <thead>
          <tr>
            <th>Ítem</th>
            <th>Actual</th>
            <th>Meta</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {tabItems.map(i => (
            <tr key={i.id}>
              <td className={styles.itemName}>{i.item}</td>
              <td className={styles.qty}>{i.current_quantity}</td>
              <td className={styles.qty}>
                {editingId === i.id ? (
                  <input
                    className={styles.qtyInput}
                    type="number"
                    min="1"
                    value={editQty}
                    onChange={e => setEditQty(e.target.value)}
                    onBlur={() => commitEdit(i.id)}
                    onKeyDown={e => e.key === "Enter" && commitEdit(i.id)}
                    autoFocus
                  />
                ) : (
                  <span
                    className={styles.qtyEditable}
                    onClick={() => startEdit(i.id, i.desired_quantity)}
                    title="Clic para editar"
                  >
                    {i.desired_quantity}
                  </span>
                )}
              </td>
              <td>
                <button className={styles.deleteBtn} onClick={() => handleDelete(i.id)}>×</button>
              </td>
            </tr>
          ))}
          <tr className={styles.addRow}>
            <td>
              <textarea
                className={styles.addInput}
                placeholder={DESCRIPTIONS[activeTab]}
                value={newItem.item}
                rows={2}
                onChange={e => setNewItem(p => ({ ...p, item: e.target.value }))}
                onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); handleAdd(e); } }}
              />
            </td>
            <td className={styles.qty}>—</td>
            <td className={styles.qty}>
              <input
                className={styles.qtyInput}
                type="number"
                min="1"
                value={newItem.desired_quantity}
                onChange={e => setNewItem(p => ({ ...p, desired_quantity: parseInt(e.target.value, 10) || 1 }))}
              />
            </td>
            <td>
              <button className={styles.addBtn} onClick={handleAdd}>+</button>
            </td>
          </tr>
        </tbody>
      </table>
    </CollapsibleSection>
  );
}
