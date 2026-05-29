import { useState } from "react";
import styles from "./CollapsibleSection.module.css";

export default function CollapsibleSection({ title, description, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  const [infoOpen, setInfoOpen] = useState(false);

  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <button
          className={styles.toggle}
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
        >
          <span className={styles.title}>{title}</span>
          <span className={styles.chevron}>{open ? "▲" : "▼"}</span>
        </button>
        {description && (
          <button
            className={styles.infoBtn}
            onClick={() => setInfoOpen((o) => !o)}
            aria-label="Más información"
            aria-expanded={infoOpen}
          >
            ?
          </button>
        )}
      </div>
      {description && infoOpen && (
        <p className={styles.infoText}>{description}</p>
      )}
      {open && <div className={styles.body}>{children}</div>}
    </section>
  );
}
