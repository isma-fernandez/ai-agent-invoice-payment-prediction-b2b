import pandas as pd
from src.data.cleaner import DataCleaner
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
    # Training dataset
    X, y = fe.generate_training_dataset(invoices_clean)
    X.to_pickle('data/X_auto.pkl')
    y.to_pickle('data/y_auto.pkl')
    # Agent dataset
    agent_dataset = fe.generate_full_client_data(invoices_clean)
    agent_dataset.to_pickle('data/agent_dataset_auto.pkl')
    print("\n DESPUÉS DE FEATURE ENGINEERING")
    print(f"Training dataset shape: {X.shape}")
    print(f"Agent dataset shape: {agent_dataset.shape}")
    print(f"Training info: {X.info()}")
    print(f"Agent info: {agent_dataset.info()}")



if __name__ == "__main__":
    main()
