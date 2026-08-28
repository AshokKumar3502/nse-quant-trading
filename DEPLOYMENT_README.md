# Deployment starter

Keep your existing `stock_scanner.py` in the project root. This `app.py` is a report viewer: it reads all six generated CSVs without applying mandatory filters and provides row selection -> Stock Analysis across all six reports.

## Local
`python -m streamlit run app.py`

## Reports expected
- output/all_scores.csv
- output/next_day_candidates.csv
- output/swing_candidates.csv
- output/historical_setup_stats.csv
- output/position_selection.csv
- output/high_priority_overlap.csv

## Daily automation
Copy `.github/workflows/daily_scanner.yml` into the repository. It runs the existing scanner after market close and verifies all six reports. Do not put secrets in GitHub source files.

## Paid access architecture
Use Supabase Auth + subscription table + a payment-provider webhook (for example Razorpay). Never trust a browser flag such as `paid=true`; the webhook/backend must verify payment and update subscription status. Keep provider secret keys out of `app.py`.

## Commercial launch
The technology can be inexpensive, but selling stock research/trading recommendations in India requires appropriate regulatory/compliance review before taking subscribers.
