import pandas as pd
import asyncio
from src.data.cleaner import DataCleaner
from src.data.feature_engineering import FeatureEngineering
from src.data.manager import DataManager
from src.agent.agent import FinancialAgent

model_path = 'models/late_invoice_payment_classification.pkl'

def test_data_processing():
    """Prueba el flujo de limpieza y feature engineering con datos locales."""
    print("=" * 60)
    print("TEST: Data Processing (Cleaner + FeatureEngineering)")
    print("=" * 60)
    
    # Cargar datos
    invoices_raw = pd.read_pickle('data/outbound_invoices.pkl')
    partners_raw = pd.read_pickle('data/partners.pkl')
    print(f"Datos raw: {len(invoices_raw)} facturas, {len(partners_raw)} partners")

    # DataCleaner
    cleaner = DataCleaner()
    invoices_clean, partners_clean = cleaner.clean_raw_data(invoices_raw, partners_raw)
    print(f"Después de limpiar: {len(invoices_clean)} facturas, {len(partners_clean)} partners")

    # Separar pagadas e impagadas
    paid = invoices_clean[invoices_clean['payment_state'] == 'paid']
    unpaid = invoices_clean[invoices_clean['payment_state'] == 'not_paid']
    print(f"Pagadas: {len(paid)}, Impagadas: {len(unpaid)}")

    # FeatureEngineering
    fe = FeatureEngineering(cutoff_date='2025-03-12')
    
    # Training dataset
    X, y = fe.generate_training_dataset(invoices_clean)
    print(f"\nTraining dataset: {X.shape[0]} filas, {X.shape[1]} features")
    print(f"Distribución target:\n{y.value_counts()}")
    
    # Agent dataset
    agent_dataset = fe.generate_full_client_data(invoices_clean)
    print(f"\nAgent dataset: {agent_dataset.shape[0]} filas, {agent_dataset.shape[1]} columnas")
    
    # Test calculate_client_statistics (para un cliente específico)
    sample_partner_id = invoices_clean['partner_id'].iloc[0]
    client_invoices = agent_dataset[agent_dataset['partner_id'] == sample_partner_id]
    stats = fe.calculate_client_stats(client_invoices)
    print(f"\nEstadísticas del cliente {sample_partner_id}:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✓ Test Data Processing completado")
    return invoices_clean, partners_clean


def test_feature_engineering_methods():
    """Prueba los métodos individuales de FeatureEngineering."""
    print("\n" + "=" * 60)
    print("TEST: FeatureEngineering Methods")
    print("=" * 60)
    
    # Cargar datos limpios
    invoices_raw = pd.read_pickle('data/outbound_invoices.pkl')
    cleaner = DataCleaner()
    invoices_clean, _ = cleaner.clean_raw_data(invoices_raw)
    
    fe = FeatureEngineering(cutoff_date='2025-03-12')
    
    # Test generate_full_client_data
    full_data = fe.generate_full_client_data(invoices_clean)
    print(f"generate_full_client_data: {len(full_data)} facturas con features")
    
    # Verificar que tiene las columnas esperadas
    expected_cols = ['paid_late', 'payment_overdue_category', 'term_rounded', 
                     'num_prior_invoices', 'ratio_late_prior_invoices']
    missing = [col for col in expected_cols if col not in full_data.columns]
    if missing:
        print(f"  ⚠ Columnas faltantes: {missing}")
    else:
        print(f"  ✓ Todas las columnas esperadas presentes")
    
    # Test process_invoice_for_prediction
    sample_invoice = full_data.iloc[10]
    partner_id = sample_invoice['partner_id']
    client_history = full_data[full_data['partner_id'] == partner_id]
    
    X = fe.process_invoice_for_prediction(sample_invoice, client_history)
    print(f"\nprocess_invoice_for_prediction: {X.shape[1]} features")
    print(f"  Features: {list(X.columns)[:5]}... (total {len(X.columns)})")
    
    # Test calculate_client_statistics
    stats = fe.calculate_client_stats(client_history)
    print(f"\ncalculate_client_statistics:")
    print(f"  total_invoices: {stats['total_invoices']}")
    print(f"  on_time_ratio: {stats['on_time_ratio']:.2%}")
    print(f"  avg_delay_days: {stats['avg_delay_days']:.1f}")
    
    print("\n✓ Test FeatureEngineering completado")


async def test_manager_with_odoo():
    """Prueba el DataManager conectado a Odoo."""
    print("\n" + "=" * 60)
    print("TEST: DataManager con conexión a Odoo")
    print("=" * 60)
    
    manager = DataManager()
    
    try:
        # Conectar a Odoo
        print("Conectando a Odoo...")
        await manager.connect()
        print("✓ Conexión establecida")
        
        # Test search_clients
        print("\n--- search_clients('Elogia') ---")
        results = await manager.search_clients("Elogia", limit=3)
        if results:
            for client in results:
                print(f"  {client.id}: {client.name} ({client.country_name})")
            
            # Usar el primer resultado para los siguientes tests
            partner_id = results[0].id
            
            # Test get_client_info
            print(f"\n--- get_client_info({partner_id}) ---")
            info = await manager.get_client_info(partner_id)
            if info:
                print(f"  Nombre: {info.name}")
                print(f"  Total facturas: {info.total_invoices}")
                print(f"  Pagadas: {info.paid_invoices}, Impagadas: {info.unpaid_invoices}")
                print(f"  Vencidas: {info.overdue_invoices}")
                print(f"  On-time ratio: {info.on_time_ratio:.2%}")
                print(f"  Avg delay: {info.avg_delay_days:.1f} días")
                print(f"  Total facturado: {info.total_invoiced_eur:,.2f} €")
                print(f"  Pendiente: {info.total_outstanding_eur:,.2f} €")
            
            # Test get_client_invoices
            print(f"\n--- get_client_invoices({partner_id}, limit=5) ---")
            invoices = await manager.get_client_invoices(partner_id, limit=5)
            for inv in invoices:
                status = "✓" if inv.payment_state.value == "paid" else "✗"
                late = f" ({inv.delay_days}d tarde)" if inv.paid_late else ""
                print(f"  {status} {inv.name}: {inv.amount_eur:,.2f}€ - {inv.due_date}{late}")
            
            # Test get_client_invoices (solo impagadas)
            print(f"\n--- get_client_invoices({partner_id}, only_unpaid=True) ---")
            unpaid = await manager.get_client_invoices(partner_id, only_unpaid=True, limit=5)
            if unpaid:
                for inv in unpaid:
                    overdue = f" (vencida hace {inv.days_overdue}d)" if inv.days_overdue else ""
                    print(f"  {inv.name}: {inv.amount_eur:,.2f}€ - vence {inv.due_date}{overdue}")
            else:
                print("  No tiene facturas impagadas")
                
        else:
            print("  No se encontraron clientes")
            
        print("\n✓ Test DataManager con Odoo completado")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


async def test_predictions_with_odoo():
    """Prueba las predicciones del DataManager (requiere modelo cargado)."""
    print("\n" + "=" * 60)
    print("TEST: Predicciones con DataManager")
    print("=" * 60)
    
    manager = DataManager()
    
    try:
        await manager.connect()
        
        # Cargar modelo (ajusta la ruta según tu proyecto)

        try:
            manager.load_model(model_path)
            print(f"✓ Modelo cargado desde {model_path}")
        except FileNotFoundError:
            print(f"⚠ Modelo no encontrado en {model_path}, saltando tests de predicción")
            return
        
        # Buscar un cliente para probar
        results = await manager.search_clients("Elogia", limit=1)
        if not results:
            print("No se encontraron clientes para probar")
            return
            
        partner_id = results[0].id
        partner_name = results[0].name
        
        # Test predict_hypothetical
        print(f"\n--- predict_hypothetical({partner_name}) ---")
        prediction = await manager.predict_hypothetical(
            partner_id=partner_id,
            amount_eur=5000.0,
            payment_term_days=30
        )
        print(f"  Factura hipotética: 5.000€ a 30 días")
        print(f"  Predicción: {prediction.prediction.value}")
        print(f"  Probabilidades:")
        for cat, prob in prediction.probabilities.items():
            print(f"    {cat}: {prob:.2%}")
        
        # Test predict con factura real
        invoices = await manager.get_client_invoices(partner_id, only_unpaid=True, limit=1)
        if invoices:
            invoice_id = invoices[0].id
            print(f"\n--- predict({invoice_id}) ---")
            prediction = await manager.predict(invoice_id)
            print(f"  Factura: {prediction.invoice_name}")
            print(f"  Importe: {prediction.amount_eur:,.2f}€")
            print(f"  Predicción: {prediction.prediction.value}")
            print(f"  Probabilidades:")
            for cat, prob in prediction.probabilities.items():
                print(f"    {cat}: {prob:.2%}")
        else:
            print("\n  No hay facturas impagadas para probar predict()")
            
        print("\n✓ Test Predicciones completado")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


def test_agent():
    """Prueba básica del agente (interactivo)."""
    print("\n" + "=" * 60)
    print("TEST: Agente (modo interactivo)")
    print("=" * 60)
    
    agent = FinancialAgent()
    user_input = input("Introduce el mensaje: ")
    response = agent.process_request(user_input)
    print("\nRespuesta del agente:")
    print(response)


async def run_all_tests():
    """Ejecuta todos los tests."""
    print("\n" + "=" * 60)
    print("EJECUTANDO TODOS LOS TESTS")
    print("=" * 60 + "\n")
    
    # Tests síncronos (datos locales)
    test_data_processing()
    test_feature_engineering_methods()
    
    # Tests asíncronos (requieren conexión a Odoo)
    try:
        await test_manager_with_odoo()
        await test_predictions_with_odoo()
    except Exception as e:
        print(f"\n⚠ Tests de Odoo fallaron: {e}")
        print("  (Asegúrate de que Odoo está accesible y las credenciales son correctas)")
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETADOS")
    print("=" * 60)


def main():
    """Punto de entrada principal."""
    import sys
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        
        if test_name == "data":
            test_data_processing()
        elif test_name == "fe":
            test_feature_engineering_methods()
        elif test_name == "manager":
            asyncio.run(test_manager_with_odoo())
        elif test_name == "predict":
            asyncio.run(test_predictions_with_odoo())
        elif test_name == "agent":
            test_agent()
        elif test_name == "all":
            asyncio.run(run_all_tests())
        else:
            print(f"Test desconocido: {test_name}")
            print("Opciones: data, fe, manager, predict, agent, all")
    else:
        # Por defecto, ejecutar todos los tests
        asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()