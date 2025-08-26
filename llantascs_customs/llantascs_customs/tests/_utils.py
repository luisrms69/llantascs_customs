import frappe
from frappe.utils import nowdate

def set_lang_es_temporarily():
    # No cambiamos System Settings; sólo el contexto de la request actual
    frappe.local.lang = "es"

def require_any_company():
    name = frappe.db.get_value("Company", {}, "name")
    if not name:
        # No creamos Company (puede requerir COA); pedimos que exista
        raise RuntimeError("No hay Company en el sitio. Instala ERPNext con datos básicos antes de correr tests.")
    return name

def get_or_create_cost_center(name: str, company: str, parent: str | None = None, is_group: int = 0) -> str:
    existing = frappe.db.get_value(
        "Cost Center",
        {"company": company, "cost_center_name": name},
        "name"
    )
    if existing:
        return existing

    if not parent:
        # Usa cualquier cost center de grupo existente como padre, si hay
        parent = frappe.db.get_value("Cost Center", {"company": company, "is_group": 1}, "name")

    cc = frappe.new_doc("Cost Center")
    cc.company = company
    cc.cost_center_name = name
    cc.is_group = is_group
    if parent:
        cc.parent_cost_center = parent
    cc.insert(ignore_permissions=True)
    return cc.name

def safe_delete(doctype: str, name: str):
    try:
        frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
    except Exception:
        # no-op si hay dependencias o ya no existe
        pass

def ensure_customer(name="__TEST__Cliente Resolver__"):
    exists = frappe.db.exists("Customer", name)
    if exists:
        return exists
    doc = frappe.new_doc("Customer")
    doc.customer_name = name
    doc.customer_type = "Individual"
    # opcional: doc.default_currency = frappe.db.get_single_value("Global Defaults", "default_currency")
    doc.insert(ignore_permissions=True)
    return doc.name

def ensure_service_item(code="__TEST__Servicio Resolver__", company=None):
    exists = frappe.db.exists("Item", code)
    if exists:
        return exists
    doc = frappe.new_doc("Item")
    doc.item_code = code
    doc.item_name = code
    doc.is_stock_item = 0  # servicio, evita flujo de inventario en tests
    doc.maintain_stock = 0
    doc.item_group = frappe.db.get_value("Item Group", {}, "name") or "All Item Groups"
    # opcionalmente setear cuentas por defecto si tu sitio lo requiere
    doc.insert(ignore_permissions=True)
    return doc.name

def get_company_and_currency():
    company = frappe.db.get_value("Company", {}, "name")
    if not company:
        raise RuntimeError("No hay Company en el sitio para crear documentos de prueba.")
    company_currency = frappe.db.get_value("Company", company, "default_currency")
    return company, company_currency

def get_receivable_account(company, prefer_currency=None):
    """Devuelve (account_name, account_currency) para una cuenta Receivable de la compañía.
       Intenta primero por moneda preferida; si no, devuelve cualquiera.
    """
    filters = {"company": company, "account_type": "Receivable", "is_group": 0}
    if prefer_currency:
        acc = frappe.db.get_value("Account", {**filters, "account_currency": prefer_currency}, ["name", "account_currency"])
        if acc:
            return acc
    acc = frappe.db.get_value("Account", filters, ["name", "account_currency"])
    if acc:
        return acc
    # último recurso: primera cuenta Asset hoja
    acc = frappe.db.get_value("Account", {"company": company, "root_type": "Asset", "is_group": 0}, ["name", "account_currency"])
    if not acc:
        raise RuntimeError("No se encontró una cuenta Receivable para la compañía en el sitio de pruebas.")
    return acc

def get_default_income_account(company):
    acc = frappe.db.get_value("Company", company, "default_income_account")
    if acc:
        return acc
    return frappe.db.get_value("Account", {"company": company, "root_type": "Income", "is_group": 0}, "name")

def ensure_selling_price_list(currency: str):
    """Devuelve (name, currency) de un Price List de venta habilitado en la moneda dada.
       Si no existe, crea uno de prueba.
    """
    name = frappe.db.get_value(
        "Price List",
        {"selling": 1, "enabled": 1, "currency": currency},
        "name"
    )
    if name:
        return name, currency

    pl = frappe.new_doc("Price List")
    pl.price_list_name = f"__TEST__Selling {currency}__"
    pl.selling = 1
    pl.enabled = 1
    pl.currency = currency
    pl.insert(ignore_permissions=True)
    return pl.name, currency

def get_leaf_cost_center(company):
    """Devuelve un Cost Center no-grupo para la compañía.
       Si no existe, crea uno bajo el root de la compañía.
    """
    cc = frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")
    if cc:
        return cc

    # intenta tomar el root de la compañía
    root = frappe.db.get_value("Company", company, "cost_center")
    if not root:
        root = frappe.db.get_value("Cost Center", {"company": company, "is_group": 1}, "name")

    if not root:
        # último recurso: crea un root si no existiera ninguno (raro)
        root_doc = frappe.get_doc({
            "doctype": "Cost Center",
            "cost_center_name": "__TEST__Root CC__",
            "company": company,
            "is_group": 1
        }).insert(ignore_permissions=True)
        root = root_doc.name

    leaf = frappe.get_doc({
        "doctype": "Cost Center",
        "cost_center_name": "__TEST__CC__",
        "company": company,
        "parent_cost_center": root,
        "is_group": 0
    }).insert(ignore_permissions=True)
    return leaf.name

def create_minimal_sales_invoice(company=None, customer=None, item_code=None, rate=1000.0, qty=1.0):
    company, company_currency = get_company_and_currency()
    customer = ensure_customer(customer or "__TEST__Cliente Resolver__")
    item_code = ensure_service_item(item_code or "__TEST__Servicio Resolver__", company)
    income_account = get_default_income_account(company)

    # Cuenta por cobrar y moneda efectiva de la SI
    receivable_acc_name, receivable_acc_currency = get_receivable_account(company, prefer_currency=company_currency)

    # Asegura un Price List de venta en la misma moneda de la SI
    si_currency = receivable_acc_currency or company_currency
    pl_name, pl_currency = ensure_selling_price_list(si_currency)

    si = frappe.new_doc("Sales Invoice")
    si.company = company
    si.customer = customer
    si.posting_date = nowdate()
    si.due_date = nowdate()

    # Moneda y cuenta a cobrar coherentes
    si.currency = si_currency
    si.debit_to = receivable_acc_name

    # Campos obligatorios de Price List
    si.selling_price_list = pl_name
    si.price_list_currency = pl_currency
    si.plc_conversion_rate = 1.0  # misma moneda → 1:1

    # Ítem (servicio) para no involucrar inventario real en los tests
    row = {"item_code": item_code, "qty": qty, "rate": rate}
    if income_account:
        row["income_account"] = income_account
    # si tu sitio exige cost_center en líneas, descomenta:
    # row["cost_center"] = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
    si.append("items", row)

    si.insert(ignore_permissions=True)
    return si.name