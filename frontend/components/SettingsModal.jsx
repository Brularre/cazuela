import { useRef, useState } from "react";
import styles from "./SettingsModal.module.css";

export default function SettingsModal({ onClose }) {
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [importError, setImportError] = useState(null);
  const fileRef = useRef(null);

  async function handleExport() {
    const res = await fetch("/api/dashboard/export");
    if (!res.ok) {
      alert("No se pudo exportar. Intenta nuevamente.");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "cazuela_export.xlsx";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleImport(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setImportResult(null);
    setImportError(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch("/api/dashboard/import", {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setImportError(err.detail || "Error al importar");
      } else {
        const data = await res.json();
        setImportResult(data.imported || {});
      }
    } catch {
      setImportError("No se pudo conectar al servidor");
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  const LABELS = {
    despensa: "Despensa",
    recetas: "Recetas",
    lista_compras: "Lista de compras",
    tareas: "Tareas",
    esperando: "Esperando",
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>Ajustes</h2>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Cerrar">×</button>
        </div>

        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>Exportar datos</h3>
          <p className={styles.sectionDesc}>
            Descarga un archivo Excel (.xlsx) con tus datos: despensa, recetas,
            lista de compras, gastos, tareas y esperando. Compatible con Google Sheets.
          </p>
          <button className={styles.primaryBtn} onClick={handleExport}>
            ⬇ Exportar .xlsx
          </button>
        </section>

        <div className={styles.divider} />

        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>Importar datos</h3>
          <p className={styles.sectionDesc}>
            Sube un archivo exportado por Cazuela. Solo se agregan ítems nuevos —
            no se sobreescribe ni borra nada existente. Gastos no se importan.
          </p>
          <label className={styles.uploadLabel}>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx"
              className={styles.fileInput}
              onChange={handleImport}
              disabled={importing}
            />
            <span className={styles.primaryBtn}>
              {importing ? "Importando…" : "⬆ Elegir archivo .xlsx"}
            </span>
          </label>

          {importError && (
            <p className={styles.errorMsg}>{importError}</p>
          )}

          {importResult && (
            <div className={styles.resultBox}>
              <p className={styles.resultTitle}>Importación completada</p>
              <ul className={styles.resultList}>
                {Object.entries(importResult).map(([key, count]) => (
                  <li key={key}>
                    <span className={styles.resultLabel}>{LABELS[key] || key}:</span>{" "}
                    {count} {count === 1 ? "ítem nuevo" : "ítems nuevos"}
                  </li>
                ))}
                {Object.keys(importResult).length === 0 && (
                  <li>Sin cambios — todo ya estaba al día.</li>
                )}
              </ul>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
