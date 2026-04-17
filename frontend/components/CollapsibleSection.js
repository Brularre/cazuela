import { useState } from "react";
import styles from "./CollapsibleSection.module.css";

export default function CollapsibleSection({ title, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className={styles.section}>
      <button
        className={styles.toggle}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className={styles.title}>{title}</span>
        <span className={styles.chevron}>{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className={styles.body}>{children}</div>}
    </section>
  );
}
