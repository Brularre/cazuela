import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection.jsx";
import styles from "./ModulesSection.module.css";

const MODULE_LABELS = {
  dinero: "Dinero",
  tiempo: "Tiempo",
  comida: "Comida",
  calendario: "Calendario",
  recordatorios: "Recordatorios",
};

export default function ModulesSection({ modulos }) {
  const [state, setState] = useState(modulos || {});

  async function toggle(module) {
    const next = !state[module];
    setState((prev) => ({ ...prev, [module]: next }));
    await fetch(`/api/dashboard/modules/${module}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: next }),
    });
  }

  return (
    <CollapsibleSection
      title="Módulos"
      description="Activa o desactiva funciones de Cazuela."
    >
      <ul className={styles.list}>
        {Object.entries(MODULE_LABELS).map(([key, label]) => {
          const enabled = state[key] !== false;
          return (
            <li key={key} className={styles.item}>
              <span className={styles.label}>{label}</span>
              <button
                className={enabled ? styles.toggleOn : styles.toggleOff}
                onClick={() => toggle(key)}
                aria-label={enabled ? `Desactivar ${label}` : `Activar ${label}`}
              >
                {enabled ? "Activo" : "Inactivo"}
              </button>
            </li>
          );
        })}
      </ul>
    </CollapsibleSection>
  );
}
