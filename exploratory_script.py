# %%
from src.data.data_retriever import DataRetriever
from src.data.odoo_connector import OdooConnection
import asyncio
from config.settings import settings
import nest_asyncio
from forex_python.converter import CurrencyRates
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import requests
from datetime import datetime
nest_asyncio.apply()
pd.set_option('display.float_format', lambda x: '%.3f' % x)

# %%
def odoo_missing_values_to_null(df):
    object_cols = df.select_dtypes(include='object').columns
    print(object_cols)
    df[object_cols] = (df[object_cols].replace({False: pd.NA, '' : pd.NA, '/' : pd.NA}))
    df[object_cols] = df[object_cols].applymap(lambda x: np.nan if x == [] else x)
    return df

# %%
def convert_to_datetime(df, columns):
    for col in columns:
        try:
            # formato que no soporta nativamente to_datetime
            if df[col].astype(str).str.contains('/').any():
                df[col] = pd.to_datetime(df[col], errors='coerce', format='%d/%m/%Y')
            else:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        except Exception as e:
            print(f"Error al convertir '{col}': {e}")
    return df

# %%
def check_invalid_date_format(series, date_format='%d/%m/%Y'):
    invalid = []
    for val in series.dropna():
        val = str(val).strip()
        if val == '' or val.lower() == 'false':
            continue
        try:
            datetime.strptime(val, date_format)
        except ValueError:
            invalid.append(val)
    return pd.Series(invalid).drop_duplicates().reset_index(drop=True)

# %% [markdown]
# # Exploración de los datos

# %% [markdown]
# # 1. Estructura de la base de datos

# %% [markdown]
# ## 1.1. Modelos relevantes

# %% [markdown]
# En está sección describo los distintos modelos que deberán ser utilizados. 
# 
# También he seleccionado los campos que pueden llegar a ser importantes para el desarrollo. Cabe remarcar que con "importantes", no me refiero únicamente para entrenar el modelo de predicción de impagos, también tengo en cuenta información que el agente podría necesitar.

# %% [markdown]
# ### 1.1.1. res.company

# %% [markdown]
# Contiene información sobre las empresas que forman el grupo (no clientes):
# - id
# - name
# - currency_id (Identificador de la moneda [id, nombre])

# %% [markdown]
# ### 1.1.2. res.partner

# %% [markdown]
# Contiene información sobre los partners (clientes/proveedores):
# - id
# - name
# - email
# - phone
# - street
# - city
# - zip
# - country_id
# - customer_rank (>0 es cliente)
# - supplier_rank (>0 es proveedor)
# - category_id (sector/industria a la que pertenece)
# - is_company
# - company_type
# - company_id
# - credit
# - credit_limit
# - debit
# - debit_limit
# - industry_id
# - invoice_ids
# - total_due
# - total_invoiced
# - total_overdue
# - trust
# - unpaid_invoice_ids
# - unpaid_invoices_count

# %% [markdown]
# ### 1.1.3. account.move

# %% [markdown]
# Guarda todas las facturas y movimientos contables de la empresa, es decir, los registros de todo lo que se compra, se vende o se paga. Este será el modelo principal con el que trabajará el agente:
# - id
# - name
# - move_type ("out_invoice", "in_invoice", "out_refund", "in_refund", "entry")
# - payment_state ("not_paid", "in_payment", "paid", "partial", "reversed")
# - company_id
# - partner_id
# - currency_id
# - amount_total
# - amount_paid
# - amount_residual
# - invoice_date
# - invoice_date_due
# - payment_dates
# - date
# - create_date
# - payment_id
# - payment_ids

# %% [markdown]
# ### 1.1.4. res.currency

# %% [markdown]
# Contiene información sobre las monedas en las que se emiten facturas y se registran los movimientos:
# - id
# - name
# - symbol
# - rate

# %% [markdown]
# ### 1.1.5. res.country

# %% [markdown]
# Contiene información sobre los países:
# - id
# - name
# - code

# %% [markdown]
# ### 1.1.6. res.partner.category

# %% [markdown]
# Representa las categorías asignadas a los partners:
# - id
# - name

# %% [markdown]
# ### 1.1.7. res.partner.industry

# %% [markdown]
# Contiene información de la industria / sector económico de los partners:
# - id
# - name

# %% [markdown]
# ## 1.2. Exploración y limpieza de los datos

# %% [markdown]
# #### Conexión a Odoo

# %%
all_invoices = pd.read_pickle('all_invoices.pkl')
all_invoices['move_type'].value_counts()

# %%
odoo_connection = OdooConnection()
data_retriever = DataRetriever(odoo_connection=odoo_connection)
asyncio.run(odoo_connection.connect())


# %%
invoices_payment_term_ids = asyncio.run(odoo_connection.search_read(model='account.move', domain=[('move_type', '=', 'out_invoice')], fields=['invoice_payment_term_id']))

# %%
#company_df_original = pd.DataFrame(asyncio.run(data_retriever.get_all_companies()))
all_invoices_df_original = pd.DataFrame(asyncio.run(data_retriever.get_all_invoices()))
#partners_df_original = pd.DataFrame(asyncio.run(data_retriever.get_all_customer_partners()))
#currencies_df_original = pd.DataFrame(asyncio.run(data_retriever.get_all_currencies()))
#partner_categories_df_original = pd.DataFrame(asyncio.run(data_retriever.get_all_partner_categories()))
#industrys_df_original = pd.DataFrame(asyncio.run(data_retriever.get_all_industries()))
#invoice_lines_df_original = pd.DataFrame(asyncio.run(data_retriever.get_all_lines_of_all_outbound_invoices()))

# %%
invoice_lines_df_original.to_pickle("invoice_lines.pkl")

# %%
#company_df_original.to_pickle("companies.pkl")
#invoices_df_original.to_pickle("invoices.pkl")
#partners_df_original.to_pickle("partners.pkl")
all_invoices_df_original.to_pickle("all_invoices.pkl")
#currencies_df_original.to_pickle("currencies.pkl")
#partner_categories_df_original.to_pickle("partner_categories.pkl")
#industrys_df_original.to_pickle("industries.pkl")  

# %%
invoices_df = pd.read_pickle("invoices.pkl")
company_df = pd.read_pickle("companies.pkl")
partners_df = pd.read_pickle("partners.pkl")
currencies_df = pd.read_pickle("currencies.pkl")
partner_categories_df = pd.read_pickle("partner_categories.pkl")
industries_df = pd.read_pickle("industries.pkl")

# %%
invoices_df = invoices_df_original.copy()
company_df = company_df_original.copy()
partners_df = partners_df_original.copy()
currencies_df = currencies_df_original.copy()
partner_categories_df = partner_categories_df_original.copy()

# %%
invoices_df = pd.read_csv
company_df = company_df_original.copy()
partners_df = partners_df_original.copy()
currencies_df = currencies_df_original.copy()
partner_categories_df = partner_categories_df_original.copy()

# %% [markdown]
# ### 1.2.1. res.company

# %%
company_df

# %% [markdown]
# El grupo está formado por 12 empresas, 9 usan el euro y 3 el peso mexicano.

# %% [markdown]
# ### 1.2.2. account.move

# %% [markdown]
# #### Inspección inicial

# %%
invoices_df.head(7000)

# %% [markdown]
# A simple vista se puede apreciar:
# - Se deben convertir los valores '', [] y False (en columnas no booleanas) a NA
# - Facturas sin nombre o con formatos muy diferentes
# - Las últimas facturas aparecen impagadas por ser demasiado recientes
# - Parece que hay algunos campos que no tienen fecha de la factura
# - payment_id y payment_ids parecen no tener nada

# %% [markdown]
# Convierto los valores False / listas vacías a valores NA

# %%
invoices_df = odoo_missing_values_to_null(invoices_df)

# %%
invoices_df.info()

# %% [markdown]
# Analizando los valores null:
# - payment_ids es todo null
# - Hay 12 facturas sin fecha, 8 sin información sobre el cliente y 40 sin nombre
# - Varias facturas sin fecha del pago (impagadas o recientes)

# %% [markdown]
# A simple vista, date, create_date, payment_id y payment_ids no son de utilidad, las dos primeras no aportan ninguna información, ya tengo invoice_date, invoice_date_due y payment_dates y las dos últimas son todo False y NA.

# %%
invoices_df = invoices_df.drop(columns=['date', 'create_date', 'payment_id', 'payment_ids'])

# %% [markdown]
# Las listas company_id, partner_id y currency_id, las separaré en dos columnas cada una

# %%
invoices_df['company_name'] = invoices_df['company_id'].apply(lambda x: x[1])
invoices_df['company_id'] = invoices_df['company_id'].apply(lambda x: x[0])

# %%
invoices_df['partner_name'] = invoices_df['partner_id'].apply(lambda x: x[1] if isinstance(x, list) else pd.NA)
invoices_df['partner_id'] = invoices_df['partner_id'].apply(lambda x: x[0] if isinstance(x, list) else pd.NA)
invoices_df['currency_name'] = invoices_df['currency_id'].apply(lambda x: x[1])
invoices_df['currency_id'] = invoices_df['currency_id'].apply(lambda x: x[0])

# %%
invoices_df.head(10000)

# %%
invoices_df["id"].duplicated().sum()

# %% [markdown]
# No hay duplicados

# %%
invoices_df.nunique()

# %% [markdown]
# Se puede apreciar:
# - Varios nombres de facturas vacíos y duplicados como se ha visto antes
# - Aunque las empresas trabajan con dos monedas internamente, han operado con clientes en 6 monedas diferentes, habrá que hacer las conversiones
# - Parece que amount_paid no tiene ningún valor (0) por tanto, tampoco aporta ninguna información, amount_residual ya tiene lo que falta por pagar, se puede inferir la cantidad pagada
# - Todos los otros campos corresponden a lo esperado

# %% [markdown]
# #### amount_paid

# %%
invoices_df['amount_paid'].mean()

# %%
invoices_df = invoices_df.drop(columns=['amount_paid'])

# %% [markdown]
# #### name

# %% [markdown]
# Todas las facturas sin nombre no han sido pagadas

# %%
invoices_na_name = invoices_df[invoices_df["name"].isna()]

# %%
invoices_na_name.head()

# %%
for col in invoices_na_name.columns:
    print(f"Columna: {col}")
    print(invoices_na_name[col].unique())

# %% [markdown]
# Parece ser que todas las facturas sin nombre, son pruebas o drafts de facturas que no llegaron a venta, por tanto se pueden eliminar:

# %%
size_na_name = len(invoices_na_name)
count_no_invoice = 0
count_draft_invoice = 0
invoices_no_draft = []
for id in invoices_na_name['id']:
    lines = asyncio.run(data_retriever.get_invoice_line_by_invoice_id(invoice_id=id))
    if len(lines) > 0:
        if 'Draft Invoice' in lines[0]['move_id'][1]:
            count_draft_invoice += 1
        else:
            invoices_no_draft.append(lines)
    else:
        count_no_invoice += 1
print(f"Total invoices with NA name: {size_na_name}")
print(f"Invoices with no invoice lines: {count_no_invoice}")
print(f"Invoices with draft invoice lines: {count_draft_invoice}")
print(f"Invoices with invoice lines but no draft: {len(invoices_no_draft)}")
invoices_no_draft[0]

# %% [markdown]
# Elimino facturas sin nombre

# %%
invoices_df = invoices_df.dropna(subset=['name'])

# %% [markdown]
# Miro duplicados de nombres

# %%
invoices_df[invoices_df['name'].duplicated()].tail()

# %% [markdown]
# Tienen problemas de nombres únicos para facturas entre empresas, 502 facturas con nombres duplicados pero mayoritariamente de diferentes empresas (solo 3 facturas de la misma empresa con el mismo nombre), de momento no afecta demasiado pero está bien saberlo

# %%
print(f"Facturas con nombres iguales: {len(invoices_df[invoices_df['name'].duplicated()])}" )
print(f"Facturas con nombre y company_id iguales: {len(invoices_df[invoices_df.duplicated(subset=['name', 'company_id'])])}")
invoices_df[invoices_df.duplicated(subset=['name', 'company_id'])]

# %%
invoices_df['name'].info()
invoices_df['name'].nunique()
invoices_df['name'].isna().sum()

# %% [markdown]
# #### payment_state

# %%
invoices_df['payment_state'].value_counts()

# %% [markdown]
# **Facturas revertidas**

# %% [markdown]
# Una factura revertida puede ser por muchos motivos, desde una devolución legítima, una cancelación o un error.

# %%
reversed_invoices = invoices_df[invoices_df['payment_state'] == 'reversed']

# %%
valid_reversed_ids = {}
for id in reversed_invoices['id']:
    reversed_move_id = asyncio.run(odoo_connection.search_read('account.move' , [('id', '=', id)], ['reversal_move_id'], offset=0, limit=0))
    if reversed_move_id and reversed_move_id[0]['reversal_move_id']:
        valid_reversed_ids[id] = reversed_move_id[0]['reversal_move_id'][0]
print(valid_reversed_ids)


# %% [markdown]
# Las facturas que tienen otra factura asociada con la revertida son todas devoluciones, las que no tienen no hay forma de saber exactamente el motivo, por tanto, dada la baja concentración de estas en todo el dataset, simplemente eliminaré las filas

# %%
reversal_invoices = []
reversal_invoices_move_type = []
for reversed_id, original_id in valid_reversed_ids.items():
    reversal_invoices.append(asyncio.run(data_retriever.get_invoice_by_id(invoice_id=original_id)))
    reversal_invoices_move_type.append(reversal_invoices[-1]['move_type'])
print(reversal_invoices_move_type)

# %% [markdown]
# Elimino las facturas revertidas

# %%
invoices_df = invoices_df[~invoices_df['id'].isin(reversed_invoices['id'])]

# %%
invoices_df['payment_state'].value_counts()

# %%
invoices_df

# %% [markdown]
# **Facturas en proceso de pago**

# %% [markdown]
# Parece que todas las facturas en proceso de pago no tienen cantidades por pagar en amount_residual a diferencia de las facturas no pagas o parcialmente pagadas. Eso significa normalmente que no están conciliadas, pero como account.payment únicamente tiene pagos salientes de las empresas y no entrantes de los clientes, no puedo comprobarlo.

# %%
invoices_in_payment = invoices_df[invoices_df['payment_state'] == 'in_payment']
invoices_in_payment.head()

# %%
invoices_with_residual = invoices_df[invoices_df['amount_residual'] > 0]
invoices_with_residual_in_payment = invoices_in_payment[invoices_in_payment['amount_residual'] > 0]
print(f"Facturas en proceso de pago con amount_residual > 0: {len(invoices_with_residual_in_payment)}")
print(f"Facturas con amount_residual > 0: {len(invoices_with_residual)}")
invoices_with_residual.head()

# %%
invoices_df.to_pickle("invoices_cleanedv1.pkl")

# %%
invoices_df = pd.read_pickle("invoices_cleanedv1.pkl")

# %% [markdown]
# Voy a ver si en account.move.line puedo encontrar más información.

# %%
invoice_lines = []
for id in invoices_in_payment['id']:
    lines = asyncio.run(data_retriever.get_invoice_line_by_invoice_id(invoice_id=id))
    invoice_lines.append(lines)


# %%
flat_list = [item for sublist in invoice_lines for item in sublist]
invoice_lines_in_payment = pd.DataFrame(flat_list)

# %%
invoices_lines_in_payment

# %% [markdown]
# Parece ser que todas las facturas tienen lineas asociadas

# %%
invoices_lines_in_payment = odoo_missing_values_to_null(invoice_lines_in_payment)
invoices_lines_in_payment.info()

# %%
invoices_lines_in_payment['move_id'] = invoices_lines_in_payment['move_id'].apply(lambda x: x[0] if isinstance(x, list) else pd.NA)

# %%
invoices_lines_in_payment['move_id'].nunique()

# %% [markdown]
# Aunque las facturas aparecen en proceso de pago, en las lineas de la factura aparecen reconciliadas, voy a comparar con una factura no pagada

# %%
invoices_lines_in_payment['reconciled'].value_counts()

# %% [markdown]
# En el caso de la factura impagada, no aparece reconciliada, por tanto asumo que es un error y algunas facturas en proceso de pago si que estan pagadas

# %%
lines_invoice_not_paid = asyncio.run(data_retriever.get_invoice_line_by_invoice_id(198522))
pd.DataFrame(lines_invoice_not_paid)['reconciled']

# %% [markdown]
# En las facturas pagadas si que aparece y coincide con el balance el total de la factura

# %%
lines_invoice_paid = asyncio.run(data_retriever.get_invoice_line_by_invoice_id(174681))
print("Reconciled: ", lines_invoice_paid[2]['reconciled'])
print("Total amount paid:", invoices_df[invoices_df['id'] == 174681]['amount_total'].values[0])
print("Total balance line: ", lines_invoice_paid[2]['balance'])
pd.DataFrame(lines_invoice_paid)['reconciled']
lines_invoice_paid[2]['balance'] == invoices_df[invoices_df['id'] == 174681]['amount_total']

# %% [markdown]
# Compruebo que no tengan cantidades restantes por pagar y no es el caso

# %%
invoices_lines_in_payment['amount_residual'].mean()

# %% [markdown]
# Comprobando que todas las facturas en proceso de pago tengan el mismo balance que el monto total, se puede ver que todas menos una estan pagadas al 100%

# %%
invoices_lines_in_payment_reconciled = invoices_lines_in_payment[invoices_lines_in_payment['reconciled'] == True]
reconciled_in_payment = 0
not_paid = []
for move_id in invoices_lines_in_payment_reconciled['move_id']:
    related_invoice = invoices_in_payment[invoices_in_payment['id'] == move_id]
    if related_invoice['amount_total'].values[0] == invoices_lines_in_payment_reconciled[invoices_lines_in_payment_reconciled['move_id'] == move_id]['balance'].values[0]:
        reconciled_in_payment += 1
    else:
        not_paid.append(move_id)
print("Reconciled and fully paid invoices in 'in_payment' state:", reconciled_in_payment)


# %% [markdown]
# Parece un error simplemente, -1680 + 268,8 = 1948,8, y amount_residual = 0, por tanto también está pagada

# %%
invoice_lines_in_payment[invoice_lines_in_payment['move_id'] == 153724]

# %%
invoices_df[invoices_df['id'] == 153724]

# %% [markdown]
# Convierto las facturas con estado de en proceso de pago en pagadas

# %%
invoices_df['payment_state'] = invoices_df['payment_state'].apply(lambda x: 'paid' if x == 'in_payment' else x)

# %%
invoices_df.to_pickle("invoices_cleanedv3.pkl")

# %% [markdown]
# **Facturas pagadas parcialmente**

# %%
invoices_df = pd.read_pickle("invoices_cleanedv3.pkl")

# %%
invoices_df['payment_state'].value_counts()

# %%
invoices_partial = invoices_df[invoices_df['payment_state'] == 'partial']
invoices_partial

# %% [markdown]
# Voy a sacar las lineas de la factura para asegurarme de que realmente esten parcialmente pagadas

# %%
invoice_lines_partial = []
for id in invoices_partial['id']:
    lines = asyncio.run(data_retriever.get_invoice_line_by_invoice_id(invoice_id=id))
    print(f"Invoice ID: {id}, Lines retrieved: {len(lines)}")
    invoice_lines_partial.extend(lines)
invoice_lines_partial_df = pd.DataFrame(invoice_lines_partial)

# %%
invoice_lines_partial_df['move_id'] = invoice_lines_partial_df['move_id'].apply(lambda x: x[0] if isinstance(x, list) else pd.NA)

# %%
invoice_lines_partial_df.head()

# %% [markdown]
# No estan ni reconciliadas ni con 0 en el residuo por pagar, pero las facturas 174403, 149233, 139026, 104262 y 47707 tienen valores demasiado bajos por pagar, las voy a considerar como pagadas

# %%
for id in invoices_partial['id']:
    sum_balance = 0
    amount_total = invoices_partial[invoices_partial['id'] == id]['amount_total'].values[0]
    amount_residual = invoices_partial[invoices_partial['id'] == id]['amount_residual'].values[0]
    for line in invoice_lines_partial_df[invoice_lines_partial_df['move_id'] == id]['amount_residual']:
        sum_balance += line
    print(f"Invoice ID: {id}, Amount Total: {amount_total}, Amount Residual: {amount_residual}, Sum of Line Residuals: {sum_balance}")

# %%
to_paid_invoices = [174403, 149233, 139026, 104262, 47707]
invoices_df['payment_state'] = invoices_df.apply(lambda row: 'paid' if row['id'] in to_paid_invoices else row['payment_state'], axis=1)

# %% [markdown]
# Quedan 15 facturas parciales, dada la pequeña cantidad, no tiene sentido hacer una clase únicamente para las parcialmente pagadas, por tanto, las moveré a la clase de no pagadas

# %%
invoices_df['payment_state'].value_counts()

# %%
invoices_df['payment_state'] = invoices_df['payment_state'].apply(lambda x: 'not_paid' if x == 'partial' else x)
invoices_df['payment_state'].value_counts()

# %% [markdown]
# **Pagadas**

# %% [markdown]
# Simplemente voy a comprobar que realmente esten pagadas a partir de las lineas de la factura y parece que todas estan pagadas, algunos pequeños valores en amount_residual no relevantes

# %%
error_paid_invoices = []
paid_invoices = invoices_df[invoices_df['payment_state'] == 'paid']
for id in paid_invoices['id']:
    lines = asyncio.run(data_retriever.get_invoice_line_by_invoice_id(invoice_id=id))
    for line in lines:
        amount_residual = line['amount_residual']
        if amount_residual > 0:
            print(f"Invoice ID: {id}, Line ID: {line['id']}, Amount Residual: {amount_residual}")
            error_paid_invoices.append(id)
print(f"Total paid invoices with residual amount > 0: {len(error_paid_invoices)}")

    

# %% [markdown]
# **No pagadas**

# %% [markdown]
# Comprobaré que realmente no esten pagadas

# %%
invoice_lines_df_original['move_id'] = invoice_lines_df_original['move_id'].apply(lambda x: x[0] if isinstance(x, list) else pd.NA)

# %% [markdown]
# Parece que todas estan sin pagar, ni estan reconciliadas ni tienen amount_residual != 0 (los resultados del código de abajo, mirando caso por caso, realmente no estan pagadas las facturas)

# %%
error_not_paid_invoices = []
not_paid_invoices = invoices_df[invoices_df['payment_state'] == 'not_paid']
for id in not_paid_invoices['id']:
    lines = invoice_lines_df_original[invoice_lines_df_original["move_id"] == id]
    if len(lines) > 0:
        amount_residual = lines.iloc[-1]['amount_residual']
        if amount_residual == 0: #and lines.iloc[-1]['reconciled'] == True:
            print(f"Invoice ID: {id}, Line ID: {lines.iloc[-1]['id']}, Amount Residual: {amount_residual}")
            error_not_paid_invoices.append(id)

# %%
invoice_lines_df_original[invoice_lines_df_original["move_id"] == 185257]


# %%
invoices_df.to_pickle("invoices_cleanedv4.pkl")

# %% [markdown]
# #### partner_id && partner name

# %% [markdown]
# 4 facturas sin partner, voy a investigar si puedo sacar algo de las lineas de las facturas

# %%
invoices_df['partner_id'].info()
print(invoices_df['partner_id'].isna().sum())
print(invoices_df['partner_id'].nunique())

# %%
invoices_without_partner = invoices_df[invoices_df['partner_id'].isna()]
invoices_without_partner

# %% [markdown]
# No tienen lineas de factura asociadas, asumo que son pruebas o errores, las elimino y ya

# %%

lines_temp_df = pd.DataFrame()
invoice_lines_df = invoice_lines_df_original.copy()
for id in invoices_without_partner['id']:
    lines = invoice_lines_df[invoice_lines_df['move_id'] == id]
    print(lines)
    lines_temp_df = pd.concat([lines_temp_df, lines], ignore_index=True)
lines_temp_df


# %%

invoices_df = invoices_df.dropna(subset=['partner_id'])

# %% [markdown]
# Ahora con el partner name y ya estaria

# %%
invoices_df['partner_name'].info()
print(invoices_df['partner_name'].isna().sum())
print(invoices_df['partner_name'].nunique())

# %%
invoices_df.to_pickle("invoices_cleanedv4.pkl")

# %% [markdown]
# #### amount_total y amount_residual

# %%
invoices_df = pd.read_pickle("invoices_cleanedv4.pkl")

# %% [markdown]
# Valores muy grandes (probablemente por la moneda), alta concentración de facturas de bajo importe, algunas facturas con valores erroneos en amount_total (0?)

# %%
invoices_df[['amount_total', 'amount_residual']].describe()

# %%
invoices_df[invoices_df['amount_total'] == 0]

# %% [markdown]
# Las elimino

# %%
invoices_df = invoices_df.drop(invoices_df[invoices_df['amount_total'] == 0].index)

# %%
invoices_df[invoices_df['amount_total'] < 1]

# %%
invoices_df[['amount_total', 'amount_residual']].describe()

# %%
currencies_df = pd.DataFrame(asyncio.run(odoo_connection.search_read('res.currency', [], [], offset=0, limit=0)))

# %% [markdown]
# Los rates son erróneos o no actualizados...

# %%
# pip install pandas-datareader
currencies_df

# %%
invoices_df['currency_name'].unique()

# %% [markdown]
# Usaré los datos del banco central europeo

# %%
c = CurrencyRates()

rates = {}
rates['COP'] = 0.00022  # Valor fijo temporal
for currency in currencies_df['name']:
    if currency != 'EUR':
        try:
            rate = c.get_rate(currency, 'EUR')
            rates[currency] = rate
        except Exception as e:
            print(f"Error retrieving rate for {currency}: {e}")

invoices_df['amount_total_eur'] = invoices_df.apply(lambda row: row['amount_total'] * rates.get(row['currency_name'], 1) if row['currency_name'] != 'EUR' else row['amount_total'], axis=1)
invoices_df['amount_residual_eur'] = invoices_df.apply(lambda row: row['amount_residual'] * rates.get(row['currency_name'], 1) if row['currency_name'] != 'EUR' else row['amount_residual'], axis=1)

# %%
invoices_df.to_pickle("invoices_cleanedv5.pkl")

# %%
invocies_df = pd.read_pickle("invoices_cleanedv5.pkl")

# %%
invoices_df[['amount_total_eur', 'amount_residual_eur']].describe()

# %% [markdown]
# #### invoice_date y invoice_date_due

# %%
invoices_df = convert_to_datetime(invoices_df, ['invoice_date', 'invoice_date_due'])

# %%
invoices_df[['invoice_date', 'invoice_date_due']].info()

# %% [markdown]
# invoice_date tiene un null, voy a verlo

# %%
invoices_df[invoices_df['invoice_date'].isna()]

# %% [markdown]
# No tiene lineas de factura elimino y ya está

# %%
invoices_lines = pd.read_pickle("invoice_lines.pkl")
invoices_lines[invoices_lines_in_payment['move_id'] == 196522]

# %%
invoices_df = invoices_df.dropna(subset=['invoice_date'])

# %%
invoices_df.isna().sum()

# %% [markdown]
# #### Payment_dates

# %% [markdown]
# Muchos nulls en payment_dates principalmente por datos censurados, de momento comprobaré que no haya ninguna factura pagada sin fecha

# %%
invoices_paid_without_date = invoices_df[(invoices_df['payment_dates'].isna()) & (invoices_df['payment_state'] == 'paid')]
len(invoices_paid_without_date)

# %% [markdown]
# 39 facturas que están pagadas pero sin fecha, voy a intentar buscar las lineas

# %%
lines_paid_without_date = invoices_lines[invoices_lines['move_id'].isin(invoices_paid_without_date['id'])]
lines_paid_without_date

# %% [markdown]
# No tienen lineas, por tanto como si no existiesen

# %%
invoices_df = invoices_df[~invoices_df['id'].isin(invoices_paid_without_date['id'])]

# %%
invoices_df.to_pickle("invoices_cleanedv6.pkl")

# %%
invoices_df = pd.read_pickle("invoices_cleanedv6.pkl")

# %% [markdown]
# Facturas no pagadas pero con fecha:

# %%
invoices_unpaid_with_date = invoices_df[(~invoices_df['payment_dates'].isna()) & (invoices_df['payment_state'] == 'unpaid')]
invoices_unpaid_with_date

# %% [markdown]
# Fechas erróneas o múltiples plazos

# %%
invoices_multiple_payment_dates = invoices_df[~invoices_df['payment_dates'].isna() & ~invoices_df['payment_dates'].astype(str).str.match(r'^\d{2}/\d{2}/\d{4}$')]
invoices_multiple_payment_dates


# %% [markdown]
# Para multiples plazos de momento simplemente me quedaré con la última fecha y invoice_date_due:

# %%
invoices_df["payment_dates"] = (invoices_df["payment_dates"].astype(str).str.split(r",\s*").str[0])

# %%
invoices_df[invoices_df['id'].isin(invoices_multiple_payment_dates['id'])]

# %%
invoices_df = convert_to_datetime(invoices_df, ['payment_dates'])

# %%
invoices_df.to_pickle("invoices_cleanedv6.pkl")

# %%
invoices_df.info()

# %% [markdown]
# #### Eliminación de facturas no útiles

# %% [markdown]
# Marketplace no sirve para predecir facturas

# %%
partners_df_original = pd.read_pickle("partners.pkl")
partners_df_original = odoo_missing_values_to_null(partners_df_original)
partners_df_original = partners_df_original.dropna(subset=['name'])

marketplace_clients = partners_df_original[partners_df_original['name'].str.contains("Marketplace")]
marketplace_clients_list = marketplace_clients['id'].values.tolist()
marketplace_clients_list

# %%
invoices_df = pd.read_pickle("invoices_cleanedv6.pkl")
invoices_df = invoices_df[~invoices_df['partner_id'].isin(marketplace_clients_list)]
invoices_df.to_pickle("invoices_cleanedv7.pkl")

# %% [markdown]
# #### invoice_payment_term_id

# %%
invoices_df = pd.read_pickle("invoices_cleanedv8.pkl")
invoices_df.info()

# %%
payment_term_dict = {item['id']: item['invoice_payment_term_id'][1] if item['invoice_payment_term_id'] else pd.NA for item in invoices_payment_term_ids}
invoices_df['invoice_payment_term'] = invoices_df['id'].map(payment_term_dict)

# %%
invoices_df['invoice_payment_term'].value_counts()

# %%
invoices_df["calculated_term"] = (invoices_df["invoice_date_due"] - invoices_df["invoice_date"]).dt.days

# %%
expected_days = {
    "30 Days": 30,
    "2 Months": 60,
    "Immediate Payment": 0,
    "45 Days": 45,
    "15 Days": 15,
    "21 Days": 21,
}
invoices_df["expected_days"] = invoices_df["invoice_payment_term"].map(expected_days)

# %%
threshold = 5

valid_count = ((invoices_df["calculated_term"] - invoices_df["expected_days"]).abs() <= threshold).sum()
invalid_count = ((invoices_df["calculated_term"] - invoices_df["expected_days"]).abs() > threshold).sum()

# %%
invalid_count

# %% [markdown]
# La información de los plazos de pago o de invoice_date_due está mal, voy a confiar en invoice_date_due viendo lo caótica que es la tabla de plazos

# %% [markdown]
# ### 1.2.3. res.partner

# %%
partners_df = pd.read_pickle("partners.pkl")

# %%
partners_spain = partners_df[partners_df['country_id'].str[0] == 68]
partners_spain['vat'].to_csv("partners_spain_ids.csv", index=False)

# %% [markdown]
# Convierto [], "" y False en objetos a null

# %%
partners_df = odoo_missing_values_to_null(partners_df)

# %%
partners_df.info()

# %%
partners_df.isna().sum()

# %% [markdown]
# A simple vista:
# - email: prácticamente vacio para la mayoria de clientes
# - telefono, category_id, company_id, industry_id, unpaid_invoice_ids: vacio
# - una empresa sin nombre
# - varios nulls en street, city, zip, country_id, vat y invoice_ids

# %% [markdown]
# Elimino las columnas email, phone, category_id, company_id, industry_id y unpaid_invoice_ids, supplier_rank (no sirve)

# %%
partners_df = partners_df.drop(columns=['email', 'phone', 'category_id', 'company_id', 'industry_id', 'unpaid_invoice_ids', 'supplier_rank'])
partners_df.info()

# %%
partners_df[['credit', 'credit_limit', 'total_due', 'total_invoiced', 'total_overdue', 'unpaid_invoices_count']].describe()

# %% [markdown]
# credit_limit y unpaid_invoices_count no sirven

# %%
partners_df = partners_df.drop(columns=['credit_limit', 'unpaid_invoices_count'])
partners_df.info()

# %%
partners_df[~partners_df['is_company'] & partners_df['vat'].isna()]


# %% [markdown]
# Tenemos personas físicas y jurídicas, como trabajamos con operaciones B2B y por alguna razón en partners tienen contactos de personas trabajando en empresas que también estan ya incluidas, eliminaré todo lo que no sea company_type = company

# %%
partners_df['company_type'].value_counts()

# %%
partners_df = partners_df.drop(partners_df[partners_df['company_type'] != 'company'].index)
partners_df.info()

# %% [markdown]
# customer_rank tampoco sirve, todos son customers por como se extraen

# %%
partners_df = partners_df.drop('customer_rank', axis=1)

# %% [markdown]
# is_company tampoco ya hemos filtrado por tipo company

# %%
partners_df['is_company'].value_counts()

# %%
partners_df = partners_df.drop(columns=['is_company'])

# %% [markdown]
# #### trust

# %% [markdown]
# Demasiada poca información, no sirve

# %%
partners_df['trust'].value_counts()

# %%
partners_df = partners_df.drop(columns=['trust'])


# %%
partners_df.info()

# %% [markdown]
# #### name and vat

# %%
partners_identification_df = partners_df[['name', 'vat']]

# %%
partners_identification_df[partners_identification_df['name'].str.contains('Hostinger')]

# %%
partners_df.to_pickle("partners_cleanedv2.pkl")

# %% [markdown]
# Un duplicado

# %%
partners_df = partners_df.drop(partners_df[partners_df['id'] == 731].index)

# %%
partners_df

# %% [markdown]
# #### invoice_ids

# %%
all_invoices_df = pd.read_pickle("all_invoices.pkl")
all_invoices_df['move_type'].value_counts() 

# %%
original_partners_df = pd.read_pickle("partners.pkl")
invoice_sum = 0
for row in original_partners_df['invoice_ids']:
    if isinstance(row, list):
        invoice_sum += len(row)
    else:
        print(row)
print(f"Total invoices linked to partners: {invoice_sum}")

# %%
invoice_sum = 0
for row in partners_df['invoice_ids']:
    if isinstance(row, list):
        invoice_sum += len(row)
    else:
        print(row)
print(f"Total invoices linked to partners: {invoice_sum}")

# %% [markdown]
# Viendo que 64298 > 47223 (total de facturas out o in), entiendo que también tienen entrys en invoice_ids, por tanto, no me sirve, cogeré la lista final de facturas y lo haré manualmente

# %%
partners_df = pd.read_pickle("partners_cleanedv2.pkl")
invoices_df = pd.read_pickle("invoices_cleanedv7.pkl")
all_invoices_df = pd.read_pickle("all_invoices.pkl")

# %%
partners_df

# %%
original_partners_df[original_partners_df['id'] == 15076]

# %% [markdown]
# Añado las facturas de cada cliente

# %%
partners_df["invoice_ids"] = [[] for _ in range(len(partners_df))]
not_found_partners = []
for invoice_id, partner_id in zip(invoices_df['id'], invoices_df['partner_id']):
    print(partner_id)
    if partners_df[partners_df['id'] == partner_id].empty:
        print(f"Partner ID {partner_id} not found in partners_df.")
        not_found_partners.append(partner_id)
        continue
    partners_df.loc[partners_df['id'] == partner_id, 'invoice_ids'].iloc[0].append(invoice_id)  

# %% [markdown]
# Guardo lista de facturas que no son válidas (no son empresas los clientes)

# %%
len(not_found_partners)

invoice_sum = 0
for row in partners_df['invoice_ids']:
    if isinstance(row, list):
        invoice_sum += len(row)
    else:
        print(row)
print(f"Total invoices linked to partners: {invoice_sum}")

# %%
partners_df.info()

# %% [markdown]
# #### Country ID

# %% [markdown]
# Me quedo únicamente con el nombre del pais

# %%
partners_df['country_name'] = partners_df['country_id'].apply(lambda x: x[1] if isinstance(x, list) else pd.NA)
partners_df = partners_df.drop(columns=['country_id'])
partners_df

# %% [markdown]
# #### company_type

# %% [markdown]
# Elimino company_type

# %%
partners_df = partners_df.drop(columns=['company_type'])
partners_df

# %%
partners_df.to_pickle("partners_cleanedv3.pkl")

# %%
invoices_df = pd.read_pickle("invoices_cleanedv8.pkl")
invoices_df['payment_state'].value_counts()

# %%
partners_df = pd.read_pickle("partners_cleanedv3.pkl")


# %%
partners_df = odoo_missing_values_to_null(partners_df)
partners_df.info()

# %% [markdown]
# Varios clientes sin facturas, no nos sirven para el modelo

# %%
partners_df = partners_df.dropna(subset=['invoice_ids'])

# %%
partners_df

# %%
discrepancies = []
for index, row in partners_df.iterrows():
    invoice_ids = row['invoice_ids']
    total_invoiced = row['total_invoiced']
    linked_invoices = invoices_df[invoices_df['id'].isin(invoice_ids)]
    sum_amount_total = linked_invoices['amount_total'].sum()
    if not np.isclose(total_invoiced, sum_amount_total):
        discrepancies.append(row['id'])

# %% [markdown]
# Tiene sentido que no este bien después de haber quitado datos, lo haré manualmente

# %%
for index, row in partners_df.iterrows():
    invoice_ids = row['invoice_ids']
    linked_invoices = invoices_df[invoices_df['id'].isin(invoice_ids)]
    sum_amount_total = linked_invoices['amount_total'].sum()
    sum_amount_total_eur = linked_invoices['amount_total_eur'].sum()
    partners_df.at[index, 'total_invoiced'] = sum_amount_total
    partners_df.at[index, 'total_invoiced_eur'] = sum_amount_total_eur

# %% [markdown]
# Total overdue y total due realmente no sirven ahora mismo para el modelo así que las elimino

# %%
partners_df = partners_df.drop(columns=['total_overdue', 'total_due'])


# %%
partners_df[partners_df['country_name'].isna()]


# %%
partners_df.loc[partners_df["id"] == 9308, "country_name"] = "Spain"
partners_df.loc[partners_df["id"] == 13304, "country_name"] = "Mexico"
partners_df.loc[partners_df["id"] == 14264, "country_name"] = "France"
partners_df.loc[partners_df["id"] == 12514, "country_name"] = "Poland"

# %%
partners_df.info()

# %%
partners_df.to_pickle("partners_cleanedv4.pkl")

# %% [markdown]
# ### Delete not valid invoices

# %%
valid_invoices = invoices_df[~invoices_df['partner_id'].isin(not_found_partners)]
len(valid_invoices)

# %%
valid_invoices.to_pickle("invoices_cleanedv8.pkl")

# %% [markdown]
# ## 1.3 Análisis de los datos

# %% [markdown]
# ### Facturas

# %% [markdown]
# Comenzaré viendo a partir de que fecha debo eliminar facturas para evitar que facturas con due_date mayor a la última fecha de datos afecten a los resultados

# %%
invoices_df = pd.read_pickle("invoices_cleanedv8.pkl")
company_df = pd.read_pickle("companies.pkl")
invoices_df.info()

# %% [markdown]
# Analizaré la continuidad temporal de las facturas en cada empresa:

# %%
for company in invoices_df['company_id'].unique():
    subset = invoices_df[invoices_df['company_id'] == company].sort_values('invoice_date')
    plt.figure(figsize=(8, 4))
    plt.plot(subset['invoice_date'], range(len(subset)))
    plt.title(f"Evolución temporal de facturas — Empresa {company_df[company_df['id'] == company]['name'].values[0]}")
    plt.xlabel("Fecha")
    plt.ylabel("Secuencia de facturas")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# %% [markdown]
# Parece que hay algunas empresas que tienen facturas hasta octubre de 2025, mientrás que la mayoría tienen hasta finales de febrero - principios de marzo~, mirando datos cogeré la fecha 12-03-2025 como corte

# %%
mask = (invoices_df['invoice_date_due'] <= np.datetime64('2025-03-12')) | (invoices_df['payment_state']  == 'paid')
invoices_df = invoices_df[mask]

# %%
invoices_df.to_pickle("invoices_cleanedv9.pkl")

# %%
paid_invoices_df = invoices_df[invoices_df['payment_state'] == 'paid']
paid_invoices_df.to_pickle("paid_invoices.pkl")

# %% [markdown]
# Eliminaré las facturas con pago immediato, no sirven para el problema

# %%
mask = (paid_invoices_df['invoice_date_due'] == paid_invoices_df['invoice_date']) & (paid_invoices_df['invoice_date_due'] == paid_invoices_df['payment_dates'])
paid_invoices_df = paid_invoices_df[~mask]

# %% [markdown]
# Añadiré característica para saber cuántos días se ha pagado tarde

# %%
paid_invoices_df['payment_overdue_days'] = (paid_invoices_df['payment_dates'] - paid_invoices_df['invoice_date_due']).dt.days.clip(lower=0)

# %%
paid_invoices_df['payment_overdue_days'].describe()

# %% [markdown]
# Tenemos outliers, comprobaré la distribución:

# %%
plt.figure(figsize=(8,5))
plt.hist(paid_invoices_df['payment_overdue_days'], bins=30)
plt.xlabel("Días de retraso")
plt.ylabel("Cantidad de facturas")
plt.title("Distribución de los días de retraso de pago")
plt.tight_layout()
plt.show()

# %% [markdown]
# Elimnaré el 0,5% de las facturas con días de retraso más altos, mirando los datos parecen ser errores

# %%
paid_invoices_df = paid_invoices_df[paid_invoices_df['payment_overdue_days'] <= paid_invoices_df['payment_overdue_days'].quantile(0.995)]
paid_invoices_df['payment_overdue_days'].describe()

# %%
plt.figure(figsize=(8,5))
plt.hist(paid_invoices_df['payment_overdue_days'], bins=80, log=True)
plt.xlabel("Días de retraso")
plt.ylabel("Cantidad de facturas")
plt.title("Distribución de los días de retraso de pago")
plt.tight_layout()
plt.show()

# %% [markdown]
# Tiene una distribución sesgada a la derecha (right-skewed)

# %%
paid_in_time = paid_invoices_df[paid_invoices_df['payment_overdue_days'] == 0]
paid_late = paid_invoices_df[paid_invoices_df['payment_overdue_days'] > 0 ] 
print(f"Facturas pagadas a tiempo: {len(paid_in_time)}")
print(f"Facturas pagadas con retraso: {len(paid_late)}")      

# %% [markdown]
# Bastante balanceado, la mitad de facturas se pagan a tiempo, la otra mitad no

# %%
paid_invoices_df.to_pickle("paid_invoicesv1.pkl")

# %% [markdown]
# Miraré por empresas:

# %%
for company in paid_invoices_df['company_id'].unique():
    subset = paid_invoices_df[paid_invoices_df['company_id'] == company].sort_values('invoice_date')
    plt.figure(figsize=(8,5))
    plt.hist(subset['payment_overdue_days'], bins=130)
    plt.xlabel("Días de retraso")
    plt.ylabel("Cantidad de facturas")
    plt.title(f"Distribución de los días de retraso de pago — Empresa {company_df[company_df['id'] == company]['name'].values[0]}")
    plt.tight_layout()
    plt.show()
    print(f"Días de retraso promedio: {subset['payment_overdue_days'].mean():.2f}")
    print(f'Facturas pagadas a tiempo: {len(subset[subset['payment_overdue_days'] == 0])}')
    print(f'Facturas pagadas con retraso: {len(subset[subset['payment_overdue_days'] > 0])}')

# %% [markdown]
# Nada destacable, todas las empresas tienen facturas pagadas tarde, más o menos, y con diferentes promedios, ibrands medios interactivos tiene una concetración mayor de facturas pagadas con retraso

# %% [markdown]
# Miraré la distribución de los importes de las facturas

# %%
plt.figure(figsize=(8,5))
plt.hist(paid_invoices_df['amount_total_eur'].dropna(), bins=80, log=True)
plt.xlabel("Importe de la factura")
plt.ylabel("Cantidad (escala log)")
plt.title("Distribución de los importes")
plt.tight_layout()
plt.show()

# %% [markdown]
# Gran concetración de facturas pequeñas, con algunas facturas con importes muy altos, sigue una distribución sesgada a la derecha (right-skewed)

# %% [markdown]
# Miraré si hay correlación lineal entre importes y días de pago, normalizo los pagos debido a la gran diferencia entre importes

# %%
pearson = paid_invoices_df['amount_total_eur'].corr(paid_invoices_df['payment_overdue_days'], method='pearson')
pearson

# %% [markdown]
# Correlación monótona, más sentido

# %%
paid_invoices_df['log_amount_total_eur'] = np.log(paid_invoices_df['amount_total_eur'])
spaerman = paid_invoices_df['log_amount_total_eur'].corr(paid_invoices_df['payment_overdue_days'], method='spearman')
spaerman

# %% [markdown]
# No parece que haya correlación

# %% [markdown]
# Crearé intervalos de los días de pago, de momento 0 (puntual), 1-15 (leve), 16-30 (moderado), 31-60 (grave), >60 (muy grave)
# 
# Necesarios para clasificación

# %%
def payment_overdue_category(days):
    if days == 0:
        return 'Puntual'
    elif 1 <= days <= 15:
        return '1-15'
    elif 16 <= days <= 30:
        return '16-30'
    elif 31 <= days <= 60:
        return '31-60'
    else:
        return '>60'
paid_invoices_df['payment_overdue_category'] = paid_invoices_df['payment_overdue_days'].apply(payment_overdue_category)


# %%
paid_invoices_df.to_pickle("paid_invoicesv2.pkl")

# %%
paid_invoices_df['payment_overdue_category'].value_counts()

# %% [markdown]
# Crearé una columna con los plazos de pago

# %% [markdown]
# Plazos que no tienen absolutamente ningún sentido...

# %%
paid_invoices_df['term'] = (paid_invoices_df['invoice_date_due'] - paid_invoices_df['invoice_date']).dt.days
paid_invoices_df['term'] = paid_invoices_df['term'].clip(lower=0)
paid_invoices_df['term_rounded'] = (paid_invoices_df['term'] / 10).round() * 10
paid_invoices_df['term_rounded'].value_counts()

# %% [markdown]
# Un poco sketchy la verdad, pero bueno, lo haré así por ahora

# %%
def map_term(x):
    if x <= 20:
        return 0
    elif x <= 40:
        return 30
    elif x <= 55:
        return 45
    elif x <= 75:
        return 60
    elif x <= 95:
        return 90
    else:
        return ">90"
paid_invoices_df['term_mapped'] = paid_invoices_df['term'].apply(map_term)
paid_invoices_df['term_mapped'].value_counts()

# %% [markdown]
# Miraré si hay correlación, para ello primero convierto las categorias de formato categórico a ordinal

# %%
term_map = {0: 0, 30: 1, 45: 2, 60: 3, 90: 4, ">90": 5}
delay_map = {'Puntual': 0, '1-15': 1, '16-30': 2, '31-60': 3, '>60': 4}
paid_invoices_df['term_encoded'] = paid_invoices_df['term_mapped'].map(term_map)
paid_invoices_df['delay_encoded'] = paid_invoices_df['payment_overdue_category'].map(delay_map)

# %%
spaerman = paid_invoices_df['term_encoded'].corr(paid_invoices_df['delay_encoded'], method='spearman')
spaerman

# %% [markdown]
# Relación demasiado débil como para tenerla en cuenta

# %% [markdown]
# Miraré ahora las variables numéricas restantes

# %%
paid_invoices_df.info()

# %% [markdown]
# Miraré la cantidad restante por pagar (tendria que ser 0 ya que tratamos con facturas pagadas)

# %%
paid_invoices_df[['amount_residual_eur']].describe()

# %%
paid_invoices_df[paid_invoices_df['amount_residual_eur'] > 0]

# %% [markdown]
# Valores demasiado pequeños excepto en el caso de la factura 47707

# %%
invoice_lines = pd.read_pickle("invoice_lines.pkl")
invoice_lines[invoice_lines['move_id'] == 47707]


# %% [markdown]
# No hay lineas de factura, asumiré que es a causa de que es muy antigua y la contaré como pagada

# %% [markdown]
# Elimino columnas que no sirven ya

# %%
paid_invoices_df = paid_invoices_df.drop(columns=['log_amount_total_eur', 'amount_residual', 'amount_total'])
paid_invoices_df.info()

# %% [markdown]
# Comenzaré a ver las categóricas

# %%
paid_invoices_df['company_id'].value_counts()

# %% [markdown]
# La mayoria de facturas vienen de la empresa 3

# %%
paid_invoices_df['partner_id'].value_counts().head(20)

# %% [markdown]
# Algunos clientes con muchas facturas

# %%
paid_invoices_df.to_pickle("paid_invoicesv3.pkl")

# %% [markdown]
# TODO: late payment rate per category

# %% [markdown]
# ### Partners

# %%
partners_df = pd.read_pickle("partners_cleanedv4.pkl")
partners_df.info()

# %%
partners_df['invoice_ids'] = partners_df['invoice_ids'].apply(lambda x: [])
partners_df = partners_df.drop(columns=['total_invoiced'])

# %% [markdown]
# Actualizo las facturas de los clientes y los totales

# %%
for partner_id in partners_df['id']:
    invoices_partner = paid_invoices_df[paid_invoices_df['partner_id'] == partner_id]
    invoice_ids_list = invoices_partner['id'].tolist()
    partners_df.loc[partners_df['id'] == partner_id, 'invoice_ids'].iloc[0].extend(invoice_ids_list)
    partners_df.loc[partners_df['id'] == partner_id, 'total_invoiced_eur'] = invoices_partner['amount_total_eur'].sum()




    

# %% [markdown]
# Elimino clientes sin facturas

# %%
partners_df = partners_df.drop(partners_df[partners_df['total_invoiced_eur'] == 0].index)

# %%
partners_df.info()

# %% [markdown]
# Añado características útiles

# %%
partners_df['total_invoices'] = partners_df['invoice_ids'].apply(lambda x: len(x))
quantity_paid_late = len(paid_invoices_df[paid_invoices_df['payment_overdue_days'] > 0])
quantity_paid_on_time = len(paid_invoices_df[paid_invoices_df['payment_overdue_days'] == 0])
partners_df['paid_late_ratio'] = 0.0
partners_df['paid_on_time_ratio'] = 0.0
partners_df['avg_days_late'] = 0.0
for partner_id in partners_df['id']:
    # solo de las facturas pagadas con retraso
    invoices_partner_late = paid_invoices_df[(paid_invoices_df['partner_id'] == partner_id) & (paid_invoices_df['payment_overdue_days'] > 0)]
    invoices_partner_ontime = paid_invoices_df[(paid_invoices_df['partner_id'] == partner_id) & (paid_invoices_df['payment_overdue_days'] == 0)]
    quantity_paid_late_partner = len(invoices_partner_late)
    quantity_paid_on_time_partner = len(invoices_partner_ontime)
    partners_df.loc[partners_df['id'] == partner_id, 'paid_late_ratio'] = quantity_paid_late_partner / (quantity_paid_late_partner + quantity_paid_on_time_partner)
    partners_df.loc[partners_df['id'] == partner_id, 'paid_on_time_ratio'] = quantity_paid_on_time_partner / (quantity_paid_late_partner + quantity_paid_on_time_partner)
    avg_days_late = invoices_partner_late['payment_overdue_days'].mean()
    partners_df.loc[partners_df['id'] == partner_id, 'avg_days_late'] = avg_days_late
partners_df.loc[partners_df['avg_days_late'].isna(), 'avg_days_late'] = 0.0

# %%
partners_df

# %%
partners_df.to_pickle("partners_cleanedv5.pkl")

# %%
paid_invoices_df = pd.read_pickle("paid_invoicesv3.pkl")

# %% [markdown]
# ### Dataset final

# %%
dataset = paid_invoices_df.copy()
dataset[['avg_invoiced_prior', 'num_prior_invoices', 'num_late_prior_invoices', 'ratio_late_prior_invoices', 
         'total_invoice_amount_prior', 'total_invoice_amount_late_prior', 'ratio_invoice_amount_late_prior',
         'avg_delay_prior_late_invoices', 'avg_delay_prior_all', 'num_outstanding_invoices', 'num_outstanding_invoices_late'
         , 'ratio_outstanding_invoices_late', 'total_invoice_amount_outstanding', 'total_invoice_amount_outstanding_late',
         'ratio_invoice_amount_outstanding_late',
         'avg_payment_term_prior_invoices']] = 0.0


# %%
reversed_dataset = dataset.sort_values(by='invoice_date', ascending=True).reset_index(drop=True)
reversed_dataset

# %%
dataset[['due_last_three_days_month', 'due_date_second_half_month']] = False

# %%
invoices_df = pd.read_pickle("invoices_cleanedv9.pkl")
unpaid_invoices_df = invoices_df[invoices_df['payment_state'] != 'paid']

# %% [markdown]
# 

# %%
# 'num_outstanding_invoices', 'num_outstanding_invoices_late',  'ratio_outstanding_invoices_late', 'total_invoice_amount_outstanding', 'total_invoice_amount_outstanding_late', pendiente de facturas impagadas
# 'ratio_invoice_amount_outstanding_late'

grouped_partner = reversed_dataset.groupby("partner_id")
for index, row in reversed_dataset.iterrows():
    partner_id = row['partner_id']
    id = row['id']
    
    invoices_partner = grouped_partner.get_group(partner_id)
    prior_invoices_partner = invoices_partner[invoices_partner['invoice_date'] < row['invoice_date']]
    late_prior_invoices_partner = prior_invoices_partner[prior_invoices_partner['payment_overdue_days'] > 0]
    if len(prior_invoices_partner) > 0:
        dataset.loc[dataset["id"] == id, 'avg_invoiced_prior'] = prior_invoices_partner['amount_total_eur'].mean()
        dataset.loc[dataset["id"] == id, 'num_prior_invoices'] = len(prior_invoices_partner)
        dataset.loc[dataset["id"] == id, 'total_invoice_amount_prior'] = prior_invoices_partner['amount_total_eur'].sum()
        if len(late_prior_invoices_partner) > 0:
            dataset.loc[dataset["id"] == id, 'num_late_prior_invoices'] = len(late_prior_invoices_partner)
            dataset.loc[dataset["id"] == id, 'ratio_late_prior_invoices'] = len(late_prior_invoices_partner) / len(prior_invoices_partner)
            dataset.loc[dataset["id"] == id, 'total_invoice_amount_late_prior'] = late_prior_invoices_partner['amount_total_eur'].sum()
            dataset.loc[dataset["id"] == id, 'ratio_invoice_amount_late_prior'] = late_prior_invoices_partner['amount_total_eur'].sum() / prior_invoices_partner['amount_total_eur'].sum()
            dataset.loc[dataset["id"] == id, 'avg_delay_prior_late_invoices'] = late_prior_invoices_partner['payment_overdue_days'].mean()
            dataset.loc[dataset["id"] == id, 'avg_delay_prior_all'] = prior_invoices_partner['payment_overdue_days'].mean()
            due_day = row['invoice_date_due'].day
            month = row['invoice_date_due'].month
            year = row['invoice_date_due'].year
            # sumo 1 mees, resto un dia y obtengo el ultimo dia del mes original
            days_in_month = (pd.Timestamp(year, month % 12 + 1, 1) - pd.Timedelta(days=1)).day 
            if due_day > days_in_month - 3:
                dataset.loc[dataset["id"] == id, 'due_last_three_days_month'] = True
            if due_day > 15:
                dataset.loc[dataset["id"] == id, 'due_date_second_half_month'] = True
            dataset.loc[dataset["id"] == id, 'avg_payment_term_prior_invoices'] = prior_invoices_partner['term'].mean()
            # pendiente de facturas impagadas
    outstanding_invoices_partner = unpaid_invoices_df[(unpaid_invoices_df['partner_id'] == partner_id) & (unpaid_invoices_df['invoice_date'] < row['invoice_date'])]
    if len(outstanding_invoices_partner) > 0:
        dataset.loc[dataset["id"] == id, 'num_outstanding_invoices'] = len(outstanding_invoices_partner)
        late_outstanding_invoices_partner = outstanding_invoices_partner[outstanding_invoices_partner['invoice_date_due'] < pd.Timestamp(2025, 3, 12)]
        if len(late_outstanding_invoices_partner) > 0:
            dataset.loc[dataset["id"] == id, 'num_outstanding_invoices_late'] = len(late_outstanding_invoices_partner)
            dataset.loc[dataset["id"] == id, 'ratio_outstanding_invoices_late'] = len(late_outstanding_invoices_partner) / len(outstanding_invoices_partner)
            dataset.loc[dataset["id"] == id, 'total_invoice_amount_outstanding'] = outstanding_invoices_partner['amount_total_eur'].sum()
            dataset.loc[dataset["id"] == id, 'total_invoice_amount_outstanding_late'] = late_outstanding_invoices_partner['amount_total_eur'].sum()
            dataset.loc[dataset["id"] == id, 'ratio_invoice_amount_outstanding_late'] = late_outstanding_invoices_partner['amount_total_eur'].sum() / outstanding_invoices_partner['amount_total_eur'].sum()

# %%
dataset[['avg_invoiced_prior', 'num_prior_invoices', 'num_late_prior_invoices', 'ratio_late_prior_invoices', 
         'total_invoice_amount_prior', 'total_invoice_amount_late_prior', 'ratio_invoice_amount_late_prior',
         'avg_delay_prior_late_invoices', 'avg_delay_prior_all', 'num_outstanding_invoices', 'num_outstanding_invoices_late'
         , 'ratio_outstanding_invoices_late', 'total_invoice_amount_outstanding', 'total_invoice_amount_outstanding_late',
         'ratio_invoice_amount_outstanding_late']].describe()

# %%
dataset['paid_late'] = dataset['payment_overdue_days'] > 0

# %%
dataset[['due_last_three_days_month', 'due_date_second_half_month', 'paid_late']].value_counts()

# %%
dataset.to_pickle("dataset.pkl")

# %%
dataset[[
         'avg_payment_term_prior_invoices']] = 0.0

# %%
days_in_month = (pd.Timestamp(2025, 2, 1) + pd.offsets.MonthEnd(1)).day
days_in_month

# %%



