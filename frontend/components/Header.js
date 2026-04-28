import styles from "./Header.module.css";

export default function Header({ onLogout, onSettings }) {
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <img src="/logo.webp" alt="Cazuela" className={styles.logo} />
        <span className={styles.name}>Cazuela</span>
      </div>
      <div className={styles.actions}>
        <button className={styles.settings} onClick={onSettings} aria-label="Ajustes">
          ⚙
        </button>
        <button className={styles.logout} onClick={onLogout}>
          Salir
        </button>
      </div>
    </header>
  );
}
