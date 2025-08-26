import frappe

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