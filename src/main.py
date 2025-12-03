import pandas as pd
from src.data.data_cleaner import DataCleaner
from src.data.feature_engineering import FeatureEngineering


def main():
    # Cargar datos
    invoices_raw = pd.read_pickle('data/outbound_invoices.pkl')
    partners_raw = pd.read_pickle('data/partners.pkl')

    print("DATOS RAW")

    # DataCleaner
    cleaner = DataCleaner()
    invoices_clean, partners_clean = cleaner.clean_raw_data(invoices_raw, partners_raw)

    print("\n DESPUÉS DE CLEANER")

    invoices_clean.to_pickle('data/invoices_clean_auto.pkl')
    partners_clean.to_pickle('data/partners_clean_auto.pkl')

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
    dataset = fe.generate_complete_dataset(paid_processed, unpaid)

    print("\nDATASET COMPLETO")
    print(f"Shape: {dataset.shape}")
    print(f"\nColumnas históricas:")
    hist_cols = ['num_prior_invoices', 'num_late_prior_invoices', 'ratio_late_prior_invoices',
                'avg_delay_prior_all', 'num_outstanding_invoices']
    print(dataset[hist_cols].describe())
    dataset.to_pickle('data/complete_dataset_auto.pkl')

if __name__ == "__main__":
    main()
