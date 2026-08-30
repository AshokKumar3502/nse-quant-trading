# NSE Quant React Frontend

This is a new React/Vite frontend. It does not replace the existing payment server.

## Run

1. Copy `.env.example` to `.env`.
2. Set:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_API_URL`
3. `npm install`
4. `npm run dev`

## Backend contract

The frontend expects read-only endpoints:

- `GET /api/reports`
- `GET /api/reports/{report_name}`
- `GET /api/stocks/{symbol}`
- `GET /api/subscription`

Keep the existing Razorpay/payment endpoints unchanged.

`/api/stocks/{symbol}` may return:
```json
{
  "symbol": "RELIANCE",
  "signal": "BUY",
  "overview": {"PRICE": 1234, "SCORE": 92},
  "rows": [{"REPORT": "All Scores", "SCORE": 92}]
}
```

Report endpoints may return either an array of rows or `{ "rows": [...] }`.

## Access policy

Free:
- All Scores
- Historical Setup Stats
- Position Selection
- Stock Analysis
- Swing Candidates

Paid:
- Next-Day Candidates
- Swing Candidates
- High-Priority Overlap
- Position Selection
- Stock Analysis
- All other premium features

The frontend does not grant premium access by itself. Premium authorization must remain enforced by the backend.
