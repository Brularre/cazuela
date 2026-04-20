import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import CollapsibleSection from "./CollapsibleSection";
import styles from "./ExpensesSection.module.css";

function formatAmount(n) {
  return "$" + Number(n).toLocaleString("es-CL");
}

export default function ExpensesSection({ gastos }) {
  if (!gastos) return null;

  const total = gastos.weekly_total || 0;
  const budget = gastos.weekly_budget || null;
  const pct = budget ? Math.min((total / budget) * 100, 100) : 0;
  const fillColor = !budget
    ? null
    : total > budget
    ? "#E74C3C"
    : pct >= 80
    ? "#E67E22"
    : "var(--cazuela-accent)";
  const byDay = gastos.by_day || [];
  const byCategory = gastos.by_category || [];
  const monthlyTotal = gastos.monthly_total || 0;
  const monthlyEstimate = gastos.monthly_estimate || 0;
  const maxAmount = Math.max(...byDay.map((d) => d.amount), 1);

  return (
    <CollapsibleSection
      title="Gastos esta semana"
      description="Escribe 'gasté 5000 en comida' por WhatsApp para registrar un gasto. El gráfico muestra el desglose semanal y el estimado mensual."
      defaultOpen
    >
      <p className={styles.total}>{formatAmount(total)}</p>
      {budget && (
        <>
          <div className={styles.budgetBar}>
            <div
              className={styles.budgetFill}
              style={{ width: `${pct}%`, background: fillColor }}
            />
          </div>
          <p className={styles.budgetLabel}>
            {total > budget
              ? `⚠ Excedido por ${formatAmount(total - budget)}`
              : `Te quedan ${formatAmount(budget - total)} de ${formatAmount(budget)}`}
          </p>
        </>
      )}

      {byDay.length > 0 && (
        <div className={styles.chartWrapper}>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={byDay} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
              <XAxis
                dataKey="day"
                tick={{ fill: "var(--cazuela-text-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis hide />
              <Tooltip
                formatter={(v) => formatAmount(v)}
                contentStyle={{
                  background: "var(--cazuela-card)",
                  border: "1px solid var(--cazuela-border)",
                  borderRadius: 6,
                  color: "var(--cazuela-text-primary)",
                  fontSize: 12,
                }}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                {byDay.map((entry) => (
                  <Cell
                    key={entry.day}
                    fill={entry.amount === maxAmount ? "var(--cazuela-accent)" : "var(--cazuela-border)"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {byCategory.length > 0 && (
        <ul className={styles.categories}>
          {byCategory.map((c) => (
            <li key={c.category} className={styles.categoryRow}>
              <span className={styles.categoryName}>{c.category}</span>
              <span className={styles.categoryAmount}>{formatAmount(c.amount)}</span>
            </li>
          ))}
        </ul>
      )}

      {total === 0 && <p className={styles.empty}>Sin gastos esta semana.</p>}
      {total > 0 && (
        <p className={styles.monthlyEstimate}>
          Este mes llevas {formatAmount(monthlyTotal)}
          {" · "}estimado mensual: {formatAmount(monthlyEstimate)}
        </p>
      )}
      {!budget && (
        <p className={styles.tip}>
          Envía <em>presupuesto semana 150.000</em> por WhatsApp para
          activar el seguimiento de presupuesto.
        </p>
      )}
    </CollapsibleSection>
  );
}
