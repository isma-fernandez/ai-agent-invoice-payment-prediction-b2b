import pandas as pd
from src.data.data_cleaner import DataCleaner
from src.data.feature_engineering import FeatureEngineering

# Cargar datos
invoices_raw = pd.read_pickle('data/outbound_invoices.pkl')
partners_raw = pd.read_pickle('data/partners.pkl')

print("DATOS RAW")
print(f"Invoices raw: {invoices_raw.shape}")
print(invoices_raw.info())
print(f"Partners raw: {partners_raw.shape}")
print(partners_raw.info())

# DataCleaner
cleaner = DataCleaner()
invoices_clean, partners_clean = cleaner.clean_raw_data(invoices_raw, partners_raw)

print("\n DESPUÉS DE CLEANER")
print(f"Invoices clean: {invoices_clean.shape}")
print(f"\nColumnas invoices: {invoices_clean.columns.tolist()}")
print(invoices_clean.info())
print(f"Partners clean: {partners_clean.shape}")
print(f"\nColumnas partners: {partners_clean.columns.tolist()}")
print(partners_clean.info())

invoices_clean.to_pickle('data/invoices_clean_auto.pkl')
partners_clean.to_pickle('data/partners_clean_auto.pkl')

"""
# Separar pagadas e impagadas
paid = invoices_clean[invoices_clean['payment_state'] == 'paid']
unpaid = invoices_clean[invoices_clean['payment_state'] == 'not_paid']
print(f"\nPagadas: {len(paid)}, Impagadas: {len(unpaid)}")

# FeatureEngineering
fe = FeatureEngineering(cutoff_date='2025-03-12')
paid_processed = fe.process_invoice_data_for_model(invoices_clean)

print("\nDESPUÉS DE PROCESS_INVOICE_DATA")
print(f"Paid processed: {paid_processed.shape}")
print(f"\nColumnas nuevas: {[c for c in paid_processed.columns if c not in invoices_clean.columns]}")
print(f"\nCategorías: {paid_processed['payment_overdue_category'].value_counts()}")

# Dataset completo
dataset = fe.generate_complete_dataset(paid_processed, unpaid, partners_clean)

print("\nDATASET COMPLETO")
print(f"Shape: {dataset.shape}")
print(f"\nColumnas históricas:")
hist_cols = ['num_prior_invoices', 'num_late_prior_invoices', 'ratio_late_prior_invoices',
             'avg_delay_prior_all', 'num_outstanding_invoices']
print(dataset[hist_cols].describe())
"""