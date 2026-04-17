import CollapsibleSection from "./CollapsibleSection";
import styles from "./PlaceholderSection.module.css";

export default function PlaceholderSection({ title, description }) {
  return (
    <CollapsibleSection title={title}>
      <p className={styles.text}>{description || "Próximamente."}</p>
    </CollapsibleSection>
  );
}
