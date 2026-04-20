# Cazuela — Dashboard (Next.js)

Personal finance and life assistant dashboard.
Pairs with the WhatsApp backend at `../backend`.

## Stack

- Next.js (Pages router)
- Plain CSS Modules — no Tailwind
- Recharts for expense charts
- Auth: WhatsApp OTP → session cookie

## Dev setup

```bash
npm install
npm run dev   # http://localhost:3000
```

Requires the backend running locally or pointing to Railway.
Set `NEXT_PUBLIC_API_URL` if the backend is not on the same host.

## Dashboard sections

| Section | Data source |
|---------|------------|
| Gastos | expenses table, weekly + MTD |
| Pendientes | todos table |
| Esperando | waiting_on table |
| Lista de compras | pantry (below threshold) + shopping_list |
| Despensa | pantry table, grouped by category |

## Deploying

Deployed on Railway alongside the backend.
`npm run build && npm start` — no special config needed.
