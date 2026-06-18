"""Domain layer: pure FP&A logic (budgeting, forecasting, variance, ingestion).

These modules are intentionally free of FastAPI/DB imports so they can be unit-tested in
isolation. The API layer adapts persisted rows to/from these functions.
"""
