import styles from "./AddItemForm.module.css";

export default function AddItemForm({ value, onChange, onSubmit, placeholder, submitting, children }) {
  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <input
        className={styles.input}
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        maxLength={500}
      />
      {children}
      <button className={styles.btn} type="submit" disabled={submitting || !value.trim()}>
        +
      </button>
    </form>
  );
}
