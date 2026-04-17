import styles from "./Header.module.css";

export default function Header({ onLogout }) {
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <span className={styles.emoji}>🍲</span>
        <span className={styles.name}>Cazuela</span>
      </div>
      <button className={styles.logout} onClick={onLogout}>
        Salir
      </button>
    </header>
  );
}
