# Semester demo walkthrough

1. Initialize, seed, verify schema and run pytest using README. Sign in as Admin. Show two stores and the database-backed overview. Store 1 and Store 2 both have ORD-1001 without ambiguity.
2. Open Store 1 ORD-1001. It purchased two Rose Cleansers. Its return contains only one unit. Open the case and show the receipt, approved Rs. 2,500 refund, successful Rs. 2,000 installment and Rs. 500 outstanding.
3. Sign in as Accounts. Import `samples/payments-installment.csv` for Store 1. Map matching columns, validate, inspect preview and confirm. The refund is settled and its short-refund exception becomes cleared.
4. Upload the exact same file again. Confirm; the row becomes duplicate and the payment count stays unchanged.
5. Record a separate successful Rs. 100 payment allocated to refund ID 1. Show Rs. 100 overpayment and potential duplicate review. Reverse that allocation with a unique reference and reason, and show the restored settled balance.
6. Import `payments-unmatched.csv`. Show unmatched exception despite a plausible order reference. Use the explicit allocation form after reviewing evidence. A failed payment never reduces outstanding; a pending one affects it only after success.
7. Sign in as Support. Open an original order, select item quantities, create a draft, edit it and approve with a reason. Explain prevention of approved returns exceeding purchased quantity.
8. Sign in as Warehouse. Receive selected quantities with condition, inspection and disposition. Separate receipt references allow arrivals on different days. Show that refund approval controls are unavailable; the automated test also verifies a direct POST returns 403.
9. Find the approved exchange without replacement. Support creates a replacement, selecting SKU. Warehouse dispatches with carrier/tracking and confirms delivery. Accounts can record a price-difference settlement note if required. Support closes only after exact accepted warehouse quantities and resolution conditions are met.
10. Accounts filters a report to Store 1 and exports CSV/XLSX. Compare the outstanding sum to the dashboard for the same filters. Show exception assignment, notes, manual resolution/reopening, and Admin's immutable audit trail.

The demo data, reference numbers and names are fictional. No payment or courier API is called.
