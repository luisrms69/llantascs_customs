# Copyright (c) 2026, Consultoria en Negocios y Aplicaciones and Contributors
# See license.txt
"""Tests de INTEGRACIÓN y CARACTERIZACIÓN del cálculo de comisiones (flujo completo).

Usan documentos REALES de ERPNext (Company MXN, Item con stock real, Sales Invoice con
update_stock, y devolución real) para validar:

  - Regresión del flujo legacy: factura normal sin notas → claves legacy intactas y columnas
    nuevas en cero (get_sales_invoices → get_commission_rows).
  - get_sales_invoices(): inclusión/exclusión por docstatus, is_return, outstanding, fecha y CC.
  - Motivo 03 con COGS REAL (signo real de get_costo_ventas_si sobre la nota; sin mock del COGS).
  - Motivo 01 con importes reales y comisión final (redondeo del sistema).

Nota: facturacion_mexico NO está instalado en test-llantascs.localhost, por lo que la ÚNICA parte
sustituida por patch es la lectura de Factura Fiscal Mexico.fm_tipo_nota_credito (seam _ffm_tipo_map).
Todo lo demás (importes, base_net_total de la nota, COGS por SLE) proviene de documentos reales.
"""

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, getdate, nowdate

from llantascs_customs.llantascs_customs import api
from llantascs_customs.llantascs_customs.api import (
    NOTA_CREDITO_DESCUENTO,
    NOTA_CREDITO_DEVOLUCION,
    get_commission_rows,
    get_costo_ventas_si,
    get_sales_invoices,
)

RATE = 10.0  # tasa de comisión (%) usada en los tests, pasada explícitamente por rates_by_cc


def _ensure(doctype, name, doc):
    if not frappe.db.exists(doctype, name):
        frappe.get_doc(doc).insert(ignore_permissions=True)
    return name


class ComisionesIntegracionBase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # --- Prerequisitos ERPNext ausentes en un site sin setup wizard ---
        # create_default_warehouses de Company exige el Warehouse Type "Transit".
        for wt in ("Transit",):
            if not frappe.db.exists("Warehouse Type", wt):
                frappe.get_doc({"doctype": "Warehouse Type", "name": wt}).insert(
                    ignore_permissions=True
                )
        for purpose in ("Material Receipt", "Material Issue", "Material Transfer"):
            if not frappe.db.exists("Stock Entry Type", purpose):
                frappe.get_doc(
                    {"doctype": "Stock Entry Type", "name": purpose, "purpose": purpose}
                ).insert(ignore_permissions=True)

        # Custom field de facturacion_mexico ausente en este site: se crea como Data para que
        # exista la columna. La clasificación real (fm_tipo_nota_credito) se sustituye vía patch
        # de _ffm_tipo_map, pero el enlace fm_factura_fiscal_mx debe existir para la consulta batch.
        if not frappe.db.exists("Custom Field", "Sales Invoice-fm_factura_fiscal_mx"):
            from frappe.custom.doctype.custom_field.custom_field import (
                create_custom_field,
            )

            create_custom_field(
                "Sales Invoice",
                {
                    "fieldname": "fm_factura_fiscal_mx",
                    "label": "FFM (test)",
                    "fieldtype": "Data",
                },
            )
            frappe.clear_cache(doctype="Sales Invoice")

        # --- Company MXN (reusar default si sirve, si no crear una MXN) ---
        default_co = frappe.defaults.get_global_default("company")
        if (
            default_co
            and frappe.db.get_value("Company", default_co, "default_currency") == "MXN"
        ):
            cls.company = default_co
        else:
            if not frappe.db.exists("Company", "_Test LLCS Comis"):
                co = frappe.new_doc("Company")
                co.company_name = "_Test LLCS Comis"
                co.abbr = "TLC"
                co.default_currency = "MXN"
                co.country = "Mexico"
                co.insert(ignore_permissions=True)
            cls.company = "_Test LLCS Comis"
            frappe.db.set_default("company", cls.company)
        cls.abbr = frappe.db.get_value("Company", cls.company, "abbr")

        # --- Fiscal Year del año en curso ---
        today = getdate(nowdate())
        fy_name = str(today.year)
        if not frappe.db.exists("Fiscal Year", fy_name):
            fy = frappe.new_doc("Fiscal Year")
            fy.year = fy_name
            fy.year_start_date = f"{today.year}-01-01"
            fy.year_end_date = f"{today.year}-12-31"
            fy.append("companies", {"company": cls.company})
            fy.insert(ignore_permissions=True)
        else:
            fy = frappe.get_doc("Fiscal Year", fy_name)
            if cls.company not in [c.company for c in fy.companies]:
                fy.append("companies", {"company": cls.company})
                fy.save(ignore_permissions=True)

        # --- Price List de venta (site sin setup wizard no la trae) ---
        cls.price_list = "Standard Selling"
        if not frappe.db.exists("Price List", cls.price_list):
            frappe.get_doc(
                {
                    "doctype": "Price List",
                    "price_list_name": cls.price_list,
                    "selling": 1,
                    "currency": "MXN",
                    "enabled": 1,
                }
            ).insert(ignore_permissions=True)

        # --- UOM / Item Group / Warehouse ---
        _ensure("UOM", "Nos", {"doctype": "UOM", "uom_name": "Nos"})
        cls.item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
        if not cls.item_group:
            _ensure(
                "Item Group",
                "Products",
                {"doctype": "Item Group", "item_group_name": "Products", "is_group": 0},
            )
            cls.item_group = "Products"

        cls.warehouse = frappe.db.get_value(
            "Warehouse", {"company": cls.company, "is_group": 0}, "name"
        )

        # --- Cost centers (dos, para probar el filtro por CC) ---
        cls.cost_center = cls._new_cost_center("Test CC LLCS A")
        cls.cost_center_b = cls._new_cost_center("Test CC LLCS B")

        # --- Customer ---
        _ensure(
            "Customer Group",
            "All Customer Groups",
            {
                "doctype": "Customer Group",
                "customer_group_name": "All Customer Groups",
                "is_group": 1,
            },
        )
        _ensure(
            "Customer Group",
            "Individual",
            {
                "doctype": "Customer Group",
                "customer_group_name": "Individual",
                "is_group": 0,
                "parent_customer_group": "All Customer Groups",
            },
        )
        _ensure(
            "Territory",
            "All Territories",
            {
                "doctype": "Territory",
                "territory_name": "All Territories",
                "is_group": 1,
            },
        )
        _ensure(
            "Territory",
            "Rest Of The World",
            {
                "doctype": "Territory",
                "territory_name": "Rest Of The World",
                "is_group": 0,
                "parent_territory": "All Territories",
            },
        )
        cls.customer = "_Test LLCS Customer"
        if not frappe.db.exists("Customer", cls.customer):
            c = frappe.new_doc("Customer")
            c.customer_name = cls.customer
            c.customer_type = "Individual"
            c.customer_group = "Individual"
            c.territory = "Rest Of The World"
            c.insert(ignore_permissions=True)

        # --- Sales Person (get_commission_rows exige Sales Team) ---
        cls.sales_person = "_Test LLCS Vendedor"
        if not frappe.db.exists("Sales Person", cls.sales_person):
            sp = frappe.new_doc("Sales Person")
            sp.sales_person_name = cls.sales_person
            sp.insert(ignore_permissions=True)

        # --- Items: servicio (no stock) y stock (con existencias reales) ---
        cls.service_item = "_Test LLCS Servicio"
        if not frappe.db.exists("Item", cls.service_item):
            it = frappe.new_doc("Item")
            it.item_code = cls.service_item
            it.item_group = cls.item_group
            it.stock_uom = "Nos"
            it.is_stock_item = 0
            it.insert(ignore_permissions=True)

        cls.stock_item = "_Test LLCS Stock"
        if not frappe.db.exists("Item", cls.stock_item):
            it = frappe.new_doc("Item")
            it.item_code = cls.stock_item
            it.item_group = cls.item_group
            it.stock_uom = "Nos"
            it.is_stock_item = 1
            it.insert(ignore_permissions=True)

        # Existencias reales del stock item: 100 @ 10 (valuation), via Material Receipt.
        cls._ensure_stock(cls.stock_item, qty=100, rate=10.0)

        frappe.db.commit()

    def setUp(self):
        super().setUp()
        # AISLAMIENTO: cost_center único por test. ERPNext commitea al hacer submit de SI/Stock,
        # así que datos de tests hermanos persisten dentro del run; un CC propio garantiza que
        # get_sales_invoices/get_commission_rows solo vean las facturas de ESTE test.
        self.cost_center = type(self)._new_cost_center(
            f"CC {type(self).__name__[:8]} {self._testMethodName[-24:]}"
        )

    # ------------------------------------------------------------------ helpers
    @classmethod
    def _new_cost_center(cls, nombre):
        full = f"{nombre} - {cls.abbr}"
        if frappe.db.exists("Cost Center", full):
            return full
        parent = frappe.db.get_value(
            "Cost Center", {"company": cls.company, "is_group": 1}, "name"
        )
        cc = frappe.new_doc("Cost Center")
        cc.cost_center_name = nombre
        cc.company = cls.company
        cc.parent_cost_center = parent
        cc.insert(ignore_permissions=True)
        return cc.name

    @classmethod
    def _ensure_stock(cls, item_code, qty, rate):
        bin_qty = frappe.db.get_value(
            "Bin", {"item_code": item_code, "warehouse": cls.warehouse}, "actual_qty"
        )
        if bin_qty and flt(bin_qty) >= qty:
            return
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Receipt"
        se.company = cls.company
        se.append(
            "items",
            {
                "item_code": item_code,
                "qty": qty,
                "basic_rate": rate,
                "t_warehouse": cls.warehouse,
            },
        )
        se.insert(ignore_permissions=True)
        se.submit()

    def _crear_si(
        self,
        item_code,
        qty,
        rate,
        update_stock,
        cost_center=None,
        posting_date=None,
        with_team=True,
        submit=True,
    ):
        cc = cost_center or self.cost_center
        si = frappe.new_doc("Sales Invoice")
        si.customer = self.customer
        si.company = self.company
        si.currency = "MXN"
        si.conversion_rate = 1.0
        si.selling_price_list = self.price_list
        si.price_list_currency = "MXN"
        si.plc_conversion_rate = 1.0
        si.ignore_pricing_rule = 1
        si.set_posting_time = 1  # respetar posting_date (evita reset a hoy)
        si.posting_date = posting_date or nowdate()
        si.due_date = si.posting_date
        si.cost_center = cc
        si.update_stock = 1 if update_stock else 0
        row = {"item_code": item_code, "qty": qty, "rate": rate, "cost_center": cc}
        if update_stock:
            row["warehouse"] = self.warehouse
        si.append("items", row)
        if with_team:
            si.append(
                "sales_team",
                {"sales_person": self.sales_person, "allocated_percentage": 100.0},
            )
        si.insert(ignore_permissions=True)
        if submit:
            si.submit()
        return si

    def _set_outstanding(self, si_name, value):
        """Ajuste de datos de prueba: fija outstanding_amount sin flujo de pago real."""
        frappe.db.set_value("Sales Invoice", si_name, "outstanding_amount", value)

    def _rows_by_si(self, result):
        return {r["sales_invoice_id"]: r for r in result["rows"]}


# ============================================================================
# 1) CARACTERIZACIÓN — factura normal sin notas: claves legacy intactas, columnas nuevas en 0
# ============================================================================
class TestCaracterizacionLegacy(ComisionesIntegracionBase):
    LEGACY_KEYS = {
        "sales_invoice_id",
        "posting_date",
        "cost_center",
        "persona_de_ventas",
        "porcentaje_comision",
        "ingreso",
        "costo_de_ventas",
        "utilidad_transaccion",
        "total_comision",
        "folio_fiscal",
    }

    def test_factura_servicio_sin_notas_claves_legacy_y_columnas_neutras(self):
        si = self._crear_si(self.service_item, qty=1, rate=1000.0, update_stock=0)
        self._set_outstanding(si.name, 0)
        res = get_commission_rows(
            [self.cost_center],
            si.posting_date,
            si.posting_date,
            rates_by_cc={self.cost_center: RATE},
        )
        rows = self._rows_by_si(res)
        self.assertIn(si.name, rows)
        r = rows[si.name]
        # Todas las claves legacy presentes
        self.assertTrue(self.LEGACY_KEYS.issubset(set(r.keys())))
        # Servicio → COGS 0, utilidad = ingreso, comisión = 1000 * 10%
        self.assertEqual(r["ingreso"], 1000.0)
        self.assertEqual(r["costo_de_ventas"], 0.0)
        self.assertEqual(r["utilidad_transaccion"], 1000.0)
        self.assertEqual(
            r["porcentaje_comision"], 100.0
        )  # allocated_percentage del vendedor
        self.assertEqual(r["total_comision"], 100.0)
        # Columnas nuevas neutras
        self.assertEqual(r["bonificaciones_01"], 0.0)
        self.assertEqual(r["devoluciones_03"], 0.0)
        self.assertEqual(r["cogs_revertido"], 0.0)
        self.assertEqual(r["ingreso_neto"], r["ingreso"])
        self.assertEqual(r["cogs_neto"], r["costo_de_ventas"])
        self.assertEqual(r["ingreso_original"], 1000.0)
        self.assertEqual(r["tasa_comision"], RATE)

    def test_factura_stock_cogs_positivo_sin_notas(self):
        # 10 @ 100 = ingreso 1000 ; COGS = 10u * 10 valuation = 100 ; utilidad 900 ; comisión 90
        si = self._crear_si(self.stock_item, qty=10, rate=100.0, update_stock=1)
        self._set_outstanding(si.name, 0)
        res = get_commission_rows(
            [self.cost_center],
            si.posting_date,
            si.posting_date,
            rates_by_cc={self.cost_center: RATE},
        )
        r = self._rows_by_si(res)[si.name]
        self.assertEqual(r["ingreso"], 1000.0)
        self.assertEqual(r["costo_de_ventas"], 100.0)
        self.assertEqual(r["utilidad_transaccion"], 900.0)
        self.assertEqual(r["total_comision"], 90.0)
        self.assertEqual(r["cogs_original"], 100.0)
        self.assertEqual(r["cogs_revertido"], 0.0)

    def test_varias_facturas_totales_sin_duplicidad(self):
        d = nowdate()
        si1 = self._crear_si(
            self.service_item, qty=1, rate=500.0, update_stock=0, posting_date=d
        )
        si2 = self._crear_si(
            self.service_item, qty=1, rate=300.0, update_stock=0, posting_date=d
        )
        for s in (si1, si2):
            self._set_outstanding(s.name, 0)
        res = get_commission_rows(
            [self.cost_center], d, d, rates_by_cc={self.cost_center: RATE}
        )
        # Filtrar SOLO las dos facturas de este test (ERPNext puede commitear SIs de otros
        # tests de la clase; el total global no es determinístico, las filas propias sí).
        propias = [
            r for r in res["rows"] if r["sales_invoice_id"] in (si1.name, si2.name)
        ]
        ids = [r["sales_invoice_id"] for r in propias]
        # una fila por factura (un solo vendedor al 100%): sin duplicidad
        self.assertEqual(sorted(ids), sorted([si1.name, si2.name]))
        self.assertEqual(len(ids), len(set(ids)))
        # comisión individual: 500*10%=50 y 300*10%=30 ; suma de las propias = 80
        by = {r["sales_invoice_id"]: r for r in propias}
        self.assertEqual(by[si1.name]["total_comision"], 50.0)
        self.assertEqual(by[si2.name]["total_comision"], 30.0)
        self.assertEqual(flt(sum(r["total_comision"] for r in propias), 2), 80.0)

    def test_politica_negativa_contabilizar_como_cero(self):
        # COGS (100) > ingreso servicio si vendo barato → utilidad negativa.
        # Con item de stock: vendo 10 @ 5 = ingreso 50, COGS 100 → utilidad -50.
        si = self._crear_si(self.stock_item, qty=10, rate=5.0, update_stock=1)
        self._set_outstanding(si.name, 0)
        res = get_commission_rows(
            [self.cost_center],
            si.posting_date,
            si.posting_date,
            rates_by_cc={self.cost_center: RATE},
        )
        r = self._rows_by_si(res)[si.name]
        self.assertEqual(r["utilidad_transaccion"], -50.0)
        # Política default "Contabilizar como cero": comisión no negativa
        self.assertEqual(r["total_comision"], 0.0)
        self.assertLessEqual(flt(res.get("subtotal_negativas", 0)), 0.0)


# ============================================================================
# 3) get_sales_invoices() — inclusión/exclusión directa
# ============================================================================
class TestSeleccionGetSalesInvoices(ComisionesIntegracionBase):
    def _select(self, cost_centers=None, d1=None, d2=None):
        d = nowdate()
        return get_sales_invoices(cost_centers or [self.cost_center], d1 or d, d2 or d)

    def test_paid_saldo_cero_incluida(self):
        si = self._crear_si(self.service_item, 1, 1000.0, update_stock=0)
        self._set_outstanding(si.name, 0)
        self.assertIn(si.name, [x["name"] for x in self._select()])

    def test_credit_note_issued_saldo_cero_incluida(self):
        # Original con nota de crédito → ERPNext status "Credit Note Issued"; outstanding 0 → incluida.
        si = self._crear_si(self.service_item, 1, 1000.0, update_stock=0)
        self._crear_nota(si, qty=1, rate=200.0)  # crea return ligada
        self._set_outstanding(si.name, 0)
        # Recomputar status con outstanding=0 (db_set no dispara set_status).
        doc = frappe.get_doc("Sales Invoice", si.name)
        doc.set_status(update=True)
        status = frappe.db.get_value("Sales Invoice", si.name, "status")
        self.assertEqual(status, "Credit Note Issued")
        self.assertIn(si.name, [x["name"] for x in self._select()])

    def test_partly_paid_saldo_positivo_excluida(self):
        si = self._crear_si(self.service_item, 1, 1000.0, update_stock=0)
        self._set_outstanding(si.name, 400.0)
        self.assertNotIn(si.name, [x["name"] for x in self._select()])

    def test_unpaid_saldo_positivo_excluida(self):
        si = self._crear_si(self.service_item, 1, 1000.0, update_stock=0)
        self._set_outstanding(si.name, 1000.0)
        self.assertNotIn(si.name, [x["name"] for x in self._select()])

    def test_saldo_positivo_dentro_tolerancia_incluida(self):
        # Precisión de outstanding = 4 → tol = 0.00005; 0.00001 < tol → tratado como 0 → incluida.
        si = self._crear_si(self.service_item, 1, 1000.0, update_stock=0)
        self._set_outstanding(si.name, 0.00001)
        self.assertIn(si.name, [x["name"] for x in self._select()])

    def test_saldo_negativo_sobrepago_incluida(self):
        si = self._crear_si(self.service_item, 1, 1000.0, update_stock=0)
        self._set_outstanding(si.name, -50.0)
        self.assertIn(si.name, [x["name"] for x in self._select()])

    def test_is_return_excluida(self):
        si = self._crear_si(self.service_item, 1, 1000.0, update_stock=0)
        nota = self._crear_nota(si, qty=1, rate=1000.0)
        self._set_outstanding(nota.name, 0)
        # La nota (is_return=1) nunca debe seleccionarse como factura original.
        self.assertNotIn(nota.name, [x["name"] for x in self._select()])

    def test_docstatus_draft_excluida(self):
        si = self._crear_si(self.service_item, 1, 1000.0, update_stock=0, submit=False)
        self.assertEqual(si.docstatus, 0)
        self.assertNotIn(si.name, [x["name"] for x in self._select()])

    def test_filtro_fecha_excluye_fuera_de_rango(self):
        year = getdate(nowdate()).year
        si = self._crear_si(
            self.service_item, 1, 1000.0, update_stock=0, posting_date=f"{year}-01-15"
        )
        self._set_outstanding(si.name, 0)
        # Rango que NO cubre enero
        out = get_sales_invoices([self.cost_center], f"{year}-03-01", f"{year}-03-31")
        self.assertNotIn(si.name, [x["name"] for x in out])
        # Rango que SÍ cubre enero
        out2 = get_sales_invoices([self.cost_center], f"{year}-01-01", f"{year}-01-31")
        self.assertIn(si.name, [x["name"] for x in out2])

    def test_filtro_cost_center(self):
        d = nowdate()
        si_a = self._crear_si(
            self.service_item, 1, 1000.0, update_stock=0, cost_center=self.cost_center
        )
        si_b = self._crear_si(
            self.service_item, 1, 1000.0, update_stock=0, cost_center=self.cost_center_b
        )
        for s in (si_a, si_b):
            self._set_outstanding(s.name, 0)
        names_a = [x["name"] for x in get_sales_invoices([self.cost_center], d, d)]
        self.assertIn(si_a.name, names_a)
        self.assertNotIn(si_b.name, names_a)

    def _crear_nota(self, si, qty, rate):
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
            make_sales_return,
        )

        nota = make_sales_return(si.name)
        # make_sales_return arma la nota completa; ajustamos qty/rate del renglón a devolver.
        nota.items[0].qty = -abs(qty)
        nota.items[0].rate = rate
        nota.update_stock = si.update_stock
        nota.insert(ignore_permissions=True)
        nota.submit()
        return nota


# ============================================================================
# 4) MOTIVO 03 — COGS real (signo real, sin mock del costo) + resultado final
# 5) MOTIVO 01 — importes reales + comisión final
# ============================================================================
class TestMotivos0103Integracion(ComisionesIntegracionBase):
    def _crear_nota(self, si, qty, rate, update_stock):
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
            make_sales_return,
        )

        nota = make_sales_return(si.name)
        nota.items[0].qty = -abs(qty)
        nota.items[0].rate = rate
        nota.update_stock = 1 if update_stock else 0
        if update_stock:
            nota.items[0].warehouse = self.warehouse
        nota.insert(ignore_permissions=True)
        nota.submit()
        return nota

    def test_motivo03_cogs_real_signo_y_neto(self):
        # Venta: 10 @ 100 = ingreso 1000 ; COGS 10*10 = 100.
        si = self._crear_si(self.stock_item, qty=10, rate=100.0, update_stock=1)
        # Devolución parcial: 4 unidades @ 100 → ingreso -400 ; COGS revertido 4*10 = 40.
        nota = self._crear_nota(si, qty=4, rate=100.0, update_stock=1)
        self._set_outstanding(si.name, 0)

        # SIGNO REAL del COGS (sin mock): ambos positivos.
        cogs_orig = flt(get_costo_ventas_si(si.name))
        cogs_rev = flt(get_costo_ventas_si(nota.name))
        self.assertEqual(cogs_orig, 100.0)
        self.assertEqual(cogs_rev, 40.0)  # POSITIVO (magnitud), no -40
        self.assertEqual(cogs_orig - cogs_rev, 60.0)

        # Resultado final del flujo, clasificando la nota como Devolución (motivo 03).
        frappe.db.set_value(
            "Sales Invoice", nota.name, "fm_factura_fiscal_mx", nota.name
        )
        with patch.object(
            api, "_ffm_tipo_map", return_value={nota.name: NOTA_CREDITO_DEVOLUCION}
        ):
            res = get_commission_rows(
                [self.cost_center],
                si.posting_date,
                si.posting_date,
                rates_by_cc={self.cost_center: RATE},
            )
        r = {x["sales_invoice_id"]: x for x in res["rows"]}[si.name]
        self.assertEqual(r["ingreso_original"], 1000.0)
        self.assertEqual(r["devoluciones_03"], -400.0)
        self.assertEqual(r["ingreso_neto"], 600.0)
        self.assertEqual(r["cogs_original"], 100.0)
        self.assertEqual(r["cogs_revertido"], 40.0)
        self.assertEqual(r["cogs_neto"], 60.0)
        self.assertEqual(r["utilidad_neta"], 540.0)
        self.assertEqual(r["total_comision"], 54.0)  # 540 * 10%

    def test_motivo03_devolucion_total_comision_cero(self):
        si = self._crear_si(self.stock_item, qty=10, rate=100.0, update_stock=1)
        nota = self._crear_nota(si, qty=10, rate=100.0, update_stock=1)
        self._set_outstanding(si.name, 0)
        with patch.object(
            api, "_ffm_tipo_map", return_value={nota.name: NOTA_CREDITO_DEVOLUCION}
        ):
            frappe.db.set_value(
                "Sales Invoice", nota.name, "fm_factura_fiscal_mx", nota.name
            )
            res = get_commission_rows(
                [self.cost_center],
                si.posting_date,
                si.posting_date,
                rates_by_cc={self.cost_center: RATE},
            )
        r = {x["sales_invoice_id"]: x for x in res["rows"]}[si.name]
        self.assertEqual(r["ingreso_neto"], 0.0)
        self.assertEqual(r["cogs_neto"], 0.0)
        self.assertEqual(r["utilidad_neta"], 0.0)
        self.assertEqual(r["total_comision"], 0.0)

    def test_motivo01_descuento_completo_con_comision(self):
        # Venta servicio: ingreso 1000, COGS 0. Descuento (nota 01) de 200 → ingreso neto 800.
        si = self._crear_si(self.service_item, qty=1, rate=1000.0, update_stock=0)
        nota = self._crear_nota(
            si, qty=1, rate=200.0, update_stock=0
        )  # base_net_total -200
        self._set_outstanding(si.name, 0)
        self.assertEqual(
            flt(frappe.db.get_value("Sales Invoice", nota.name, "base_net_total")),
            -200.0,
        )

        with patch.object(
            api, "_ffm_tipo_map", return_value={nota.name: NOTA_CREDITO_DESCUENTO}
        ):
            frappe.db.set_value(
                "Sales Invoice", nota.name, "fm_factura_fiscal_mx", nota.name
            )
            res = get_commission_rows(
                [self.cost_center],
                si.posting_date,
                si.posting_date,
                rates_by_cc={self.cost_center: RATE},
            )
        r = {x["sales_invoice_id"]: x for x in res["rows"]}[si.name]
        self.assertEqual(r["ingreso_original"], 1000.0)
        self.assertEqual(r["bonificaciones_01"], -200.0)
        self.assertEqual(r["ingreso_neto"], 800.0)
        self.assertEqual(
            r["cogs_neto"], 0.0
        )  # motivo 01: COGS intacto (aquí 0, servicio)
        self.assertEqual(r["utilidad_neta"], 800.0)
        self.assertEqual(r["total_comision"], 80.0)  # 800 * 10%

    def test_sin_ffm_no_interrumpe_calculo(self):
        # Nota real sin FFM y sin marcadores de descuento → NO se detiene; se trata como devolución.
        cc = self.cost_center
        si = self._crear_si(
            self.service_item, qty=1, rate=1000.0, update_stock=0, cost_center=cc
        )
        self._crear_nota(
            si, qty=1, rate=200.0, update_stock=0
        )  # devolución parcial (servicio)
        self._set_outstanding(si.name, 0)
        with patch.object(
            api, "_ffm_tipo_map", return_value={}
        ):  # sin FFM → sin motivo explícito
            res = get_commission_rows(
                [cc], si.posting_date, si.posting_date, rates_by_cc={cc: RATE}
            )
        r = {x["sales_invoice_id"]: x for x in res["rows"]}[si.name]
        # Tratada como devolución: ingreso baja, COGS servicio 0, utilidad residual 800 → comisión 80.
        self.assertEqual(r["devoluciones_03"], -200.0)
        self.assertEqual(r["bonificaciones_01"], 0.0)
        self.assertEqual(r["ingreso_neto"], 800.0)
        self.assertEqual(r["cogs_neto"], 0.0)
        self.assertEqual(r["total_comision"], 80.0)

    def test_descuento_por_marcadores_reales(self):
        # Sin FFM, pero la nota lleva los marcadores de "Aplicar como Descuento": update_stock=0 y
        # todas las líneas con income_account == cuenta de descuentos. → motivo 01, COGS NO se revierte.
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
            make_sales_return,
        )

        cc = self.cost_center
        parent = frappe.db.get_value(
            "Account",
            {"company": self.company, "root_type": "Income", "is_group": 1},
            "name",
        )
        disc = f"Descuentos LLCS Test - {self.abbr}"
        if not frappe.db.exists("Account", disc):
            acc = frappe.new_doc("Account")
            acc.account_name = "Descuentos LLCS Test"
            acc.company = self.company
            acc.parent_account = parent
            acc.root_type = "Income"
            acc.insert(ignore_permissions=True)
            disc = acc.name

        si = self._crear_si(
            self.stock_item, qty=10, rate=100.0, update_stock=1, cost_center=cc
        )  # COGS 100
        nota = make_sales_return(si.name)
        nota.update_stock = 0  # un descuento no mueve inventario
        for it in nota.items:
            it.income_account = disc  # marcador contable de la acción de descuento
        nota.insert(ignore_permissions=True)
        nota.submit()
        self._set_outstanding(si.name, 0)

        with (
            patch.object(api, "_ffm_tipo_map", return_value={}),  # sin FFM
            patch.object(
                api, "get_cuenta_descuentos", return_value=disc
            ),  # cuenta de descuentos
        ):
            res = get_commission_rows(
                [cc], si.posting_date, si.posting_date, rates_by_cc={cc: RATE}
            )
        r = {x["sales_invoice_id"]: x for x in res["rows"]}[si.name]
        self.assertEqual(r["bonificaciones_01"], -1000.0)  # clasificada como descuento
        self.assertEqual(r["devoluciones_03"], 0.0)
        self.assertEqual(r["cogs_original"], 100.0)
        self.assertEqual(r["cogs_revertido"], 0.0)  # descuento NO revierte COGS
        self.assertEqual(r["cogs_neto"], 100.0)  # COGS intacto

    def test_lote_nota_sin_motivo_no_detiene_las_demas(self):
        # Un lote donde una factura tiene nota sin motivo NO debe impedir calcular las demás.
        cc = self.cost_center
        si_a = self._crear_si(
            self.service_item, qty=1, rate=500.0, update_stock=0, cost_center=cc
        )
        self._set_outstanding(si_a.name, 0)
        si_b = self._crear_si(
            self.service_item, qty=1, rate=1000.0, update_stock=0, cost_center=cc
        )
        self._crear_nota(
            si_b, qty=1, rate=1000.0, update_stock=0
        )  # devolución total, sin FFM
        self._set_outstanding(si_b.name, 0)
        with patch.object(api, "_ffm_tipo_map", return_value={}):
            res = get_commission_rows(
                [cc], si_a.posting_date, si_a.posting_date, rates_by_cc={cc: RATE}
            )
        rows = {x["sales_invoice_id"]: x for x in res["rows"]}
        self.assertIn(si_a.name, rows)  # la normal se calculó
        self.assertEqual(rows[si_a.name]["total_comision"], 50.0)
        self.assertIn(
            si_b.name, rows
        )  # la de nota sin motivo también (devolución total → 0)
        self.assertEqual(rows[si_b.name]["total_comision"], 0.0)

    def test_ffm_descuento_explicito_tiene_prioridad_sobre_inventario(self):
        # El motivo explícito de FFM manda sobre cualquier mecanismo alternativo: aunque la nota
        # haya MOVIDO inventario (parecería devolución), FFM='Descuento / Bonificación' → NO revierte
        # COGS. Confirma la prioridad #1 (FFM) frente a la evidencia de inventario.
        cc = self.cost_center
        si = self._crear_si(
            self.stock_item, qty=10, rate=100.0, update_stock=1, cost_center=cc
        )  # COGS 100
        nota = self._crear_nota(
            si, qty=10, rate=100.0, update_stock=1
        )  # nota CON stock (reingresa inventario)
        self.assertEqual(
            flt(get_costo_ventas_si(nota.name)), 100.0
        )  # inventario sí regresó
        self._set_outstanding(si.name, 0)
        frappe.db.set_value(
            "Sales Invoice", nota.name, "fm_factura_fiscal_mx", nota.name
        )
        with patch.object(
            api, "_ffm_tipo_map", return_value={nota.name: NOTA_CREDITO_DESCUENTO}
        ):
            res = get_commission_rows(
                [cc], si.posting_date, si.posting_date, rates_by_cc={cc: RATE}
            )
        r = {x["sales_invoice_id"]: x for x in res["rows"]}[si.name]
        self.assertEqual(r["bonificaciones_01"], -1000.0)  # FFM manda → descuento
        self.assertEqual(r["devoluciones_03"], 0.0)
        self.assertEqual(
            r["cogs_revertido"], 0.0
        )  # NO revierte pese al movimiento de inventario
        self.assertEqual(
            r["cogs_neto"], 100.0
        )  # COGS intacto (prioridad del motivo explícito)

    def test_ffm_devolucion_explicito_revierte(self):
        # Contraparte: FFM='Devolución de mercancía' explícito → clasifica devolución y revierte COGS.
        cc = self.cost_center
        si = self._crear_si(
            self.stock_item, qty=10, rate=100.0, update_stock=1, cost_center=cc
        )
        nota = self._crear_nota(si, qty=10, rate=100.0, update_stock=1)
        self._set_outstanding(si.name, 0)
        frappe.db.set_value(
            "Sales Invoice", nota.name, "fm_factura_fiscal_mx", nota.name
        )
        with patch.object(
            api, "_ffm_tipo_map", return_value={nota.name: NOTA_CREDITO_DEVOLUCION}
        ):
            res = get_commission_rows(
                [cc], si.posting_date, si.posting_date, rates_by_cc={cc: RATE}
            )
        r = {x["sales_invoice_id"]: x for x in res["rows"]}[si.name]
        self.assertEqual(r["devoluciones_03"], -1000.0)
        self.assertEqual(r["bonificaciones_01"], 0.0)
        self.assertEqual(r["cogs_revertido"], 100.0)  # revierte por el motivo explícito
        self.assertEqual(r["cogs_neto"], 0.0)
        self.assertEqual(r["total_comision"], 0.0)


# ============================================================================
# COGS revertido vía Delivery Note de RETORNO (corrección delimitada)
# Reproduce el flujo update_stock=0 (SI ← Delivery Note) donde el inventario regresa por una
# DN de devolución (is_return=1) y NO por la nota de crédito — caso ACC-SINV-2025-07287.
# ============================================================================
class TestCogsReturnDN(ComisionesIntegracionBase):
    def _crear_dn(self, item, qty, rate, cost_center=None):
        cc = cost_center or self.cost_center
        dn = frappe.new_doc("Delivery Note")
        dn.customer = self.customer
        dn.company = self.company
        dn.currency = "MXN"
        dn.conversion_rate = 1.0
        dn.selling_price_list = self.price_list
        dn.price_list_currency = "MXN"
        dn.plc_conversion_rate = 1.0
        dn.ignore_pricing_rule = 1
        dn.set_posting_time = 1
        dn.posting_date = nowdate()
        dn.cost_center = cc
        dn.append(
            "items",
            {
                "item_code": item,
                "qty": qty,
                "rate": rate,
                "warehouse": self.warehouse,
                "cost_center": cc,
            },
        )
        dn.insert(ignore_permissions=True)
        dn.submit()
        return dn

    def _si_desde_dn(self, dn, cost_center=None):
        from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

        cc = cost_center or self.cost_center
        si = make_sales_invoice(dn.name)
        si.selling_price_list = self.price_list
        si.price_list_currency = "MXN"
        si.plc_conversion_rate = 1.0
        si.ignore_pricing_rule = 1
        si.set_posting_time = 1
        si.cost_center = cc
        for it in si.items:
            it.cost_center = cc
        si.append(
            "sales_team",
            {"sales_person": self.sales_person, "allocated_percentage": 100.0},
        )
        si.insert(ignore_permissions=True)
        si.submit()
        return si

    def _return_dn(self, dn, qty=None):
        from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

        rdn = make_sales_return(dn.name)
        if qty is not None:
            rdn.items[0].qty = -abs(qty)
        rdn.insert(ignore_permissions=True)
        rdn.submit()
        return rdn

    def _delivered_qty(self, si_name):
        return flt(
            frappe.db.get_value(
                "Sales Invoice Item", {"parent": si_name}, "delivered_qty"
            )
        )

    def _en_get_sales_invoices(self, si):
        d = si.posting_date
        return si.name in [
            x["name"] for x in get_sales_invoices([si.cost_center], d, d)
        ]

    def _entregar_si(self, si):
        # Flujo REAL: SI primero (update_stock=0), luego DN contra la SI (against_sales_invoice).
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
            make_delivery_note,
        )

        dn = make_delivery_note(si.name)
        for it in dn.items:
            it.warehouse = self.warehouse
        dn.insert(ignore_permissions=True)
        dn.submit()
        return dn

    def test_filtro_entrega_no_excluye_devoluciones(self):
        # DIAGNÓSTICO del filtro _delivered: en el flujo real SI→DN, delivered_qty es lo entregado
        # BRUTO y NO se reduce por una DN de retorno (return_against=DN). Por tanto una factura
        # entregada y luego devuelta (total o parcial) SIGUE pasando get_sales_invoices → el filtro
        # es correcto y no excluye devoluciones legítimas.
        cc = self.cost_center
        si = self._crear_si(
            self.stock_item, qty=4, rate=100.0, update_stock=0, cost_center=cc
        )
        self._set_outstanding(si.name, 0)
        self.assertEqual(self._delivered_qty(si.name), 0.0)  # sin entregar
        self.assertFalse(self._en_get_sales_invoices(si))  # excluida (correcto)
        dn = self._entregar_si(si)
        self.assertEqual(self._delivered_qty(si.name), 4.0)
        self.assertTrue(self._en_get_sales_invoices(si))  # entregada → incluida
        self._return_dn(dn, qty=2)  # devolución parcial
        self.assertEqual(self._delivered_qty(si.name), 4.0)  # NO se reduce
        self.assertTrue(self._en_get_sales_invoices(si))  # sigue incluida
        self._return_dn(dn, qty=2)  # devolución total
        self.assertEqual(self._delivered_qty(si.name), 4.0)  # NO se reduce
        self.assertTrue(self._en_get_sales_invoices(si))  # sigue incluida

    def test_flujo_entrega_completa_sin_devolucion(self):
        # Full flow: SI→DN entregada, sin devolución → comisión sobre utilidad completa.
        cc = self.cost_center
        si = self._crear_si(
            self.stock_item, qty=4, rate=100.0, update_stock=0, cost_center=cc
        )
        self._entregar_si(si)  # entrega completa (COGS 4*10=40)
        self._set_outstanding(si.name, 0)
        with patch.object(api, "_ffm_tipo_map", return_value={}):
            res = get_commission_rows(
                [cc], si.posting_date, si.posting_date, rates_by_cc={cc: RATE}
            )
        r = {x["sales_invoice_id"]: x for x in res["rows"]}[si.name]
        self.assertEqual(r["ingreso_neto"], 400.0)
        self.assertEqual(r["cogs_original"], 40.0)
        self.assertEqual(r["cogs_neto"], 40.0)
        self.assertEqual(r["utilidad_neta"], 360.0)
        self.assertEqual(r["total_comision"], 36.0)

    def test_flujo_entrega_completa_devolucion_total(self):
        # Full flow: SI→DN entregada + devolución TOTAL vía DN de retorno + nota total → comisión 0.
        cc = self.cost_center
        si = self._crear_si(
            self.stock_item, qty=4, rate=100.0, update_stock=0, cost_center=cc
        )
        dn = self._entregar_si(si)  # COGS 40
        self._return_dn(dn, qty=4)  # retorno total → COGS revertido 40
        self._nota(si, rate=100.0)  # nota -400 (revierte ingreso)
        self._set_outstanding(si.name, 0)
        with patch.object(api, "_ffm_tipo_map", return_value={}):
            res = get_commission_rows(
                [cc], si.posting_date, si.posting_date, rates_by_cc={cc: RATE}
            )
        r = {x["sales_invoice_id"]: x for x in res["rows"]}[si.name]
        self.assertEqual(r["ingreso_neto"], 0.0)
        self.assertEqual(r["cogs_original"], 40.0)
        self.assertEqual(r["cogs_revertido"], 40.0)  # DN de retorno
        self.assertEqual(r["cogs_neto"], 0.0)
        self.assertEqual(r["utilidad_neta"], 0.0)
        self.assertEqual(r["total_comision"], 0.0)

    def test_flujo_entrega_completa_devolucion_parcial(self):
        # Full flow: SI→DN entregada + devolución PARCIAL (2 de 4) → comisión sobre residual.
        cc = self.cost_center
        si = self._crear_si(
            self.stock_item, qty=4, rate=100.0, update_stock=0, cost_center=cc
        )
        dn = self._entregar_si(si)  # COGS 40
        self._return_dn(dn, qty=2)  # retorno parcial → COGS revertido 20
        self._nota(si, rate=50.0)  # nota -200 (revierte ingreso de lo devuelto)
        self._set_outstanding(si.name, 0)
        with patch.object(api, "_ffm_tipo_map", return_value={}):
            res = get_commission_rows(
                [cc], si.posting_date, si.posting_date, rates_by_cc={cc: RATE}
            )
        r = {x["sales_invoice_id"]: x for x in res["rows"]}[si.name]
        self.assertEqual(r["ingreso_neto"], 200.0)  # 400 − 200
        self.assertEqual(r["cogs_original"], 40.0)
        self.assertEqual(r["cogs_revertido"], 20.0)  # DN de retorno (2 u)
        self.assertEqual(r["cogs_neto"], 20.0)
        self.assertEqual(r["utilidad_neta"], 180.0)
        self.assertEqual(r["total_comision"], 18.0)

    def _nota_sin_stock(self, si):
        # Nota de crédito que revierte SOLO el ingreso, sin vínculo de inventario — fiel a las notas
        # reales del cliente (p. ej. ACC-SINV-2025-07477), cuyos renglones NO enlazan la DN de
        # salida. Se despoja delivery_note/dn_detail para que get_costo_ventas_si(nota) sea 0 y el
        # reverso de COGS provenga exclusivamente de la DN de retorno.
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
            make_sales_return,
        )

        nota = make_sales_return(si.name)
        nota.update_stock = 0
        for it in nota.items:
            it.delivery_note = None
            it.dn_detail = None
        nota.insert(ignore_permissions=True)
        nota.submit()
        return nota

    def _adj(self, si, nota):
        frappe.db.set_value(
            "Sales Invoice", nota.name, "fm_factura_fiscal_mx", nota.name
        )
        with patch.object(
            api, "_ffm_tipo_map", return_value={nota.name: NOTA_CREDITO_DEVOLUCION}
        ):
            return api._build_credit_note_adjustments([si.name]).get(si.name, {})

    def _rate(self, cc):
        return {cc: RATE}

    def test_us0_forward_dn_y_return_dn_netea_cero(self):
        # Reproduce ACC-SINV-2025-07287: entrega por DN, retorno por DN de devolución, nota sin stock.
        # Se valida el neteo en _build_credit_note_adjustments / _net_from_credit_notes (aislado del
        # filtro de entrega de get_sales_invoices, que es ortogonal a esta corrección de COGS).
        cc = self.cost_center
        dn = self._crear_dn(
            self.stock_item, qty=4, rate=100.0, cost_center=cc
        )  # COGS out 40
        si = self._si_desde_dn(dn, cc)  # update_stock=0, ingreso 400
        self.assertEqual(si.update_stock, 0)
        rdn = self._return_dn(dn)  # DN de retorno: COGS back 40
        self.assertEqual(rdn.is_return, 1)
        nota = self._nota_sin_stock(
            si
        )  # nota revierte ingreso -400, SIN vínculo de inventario

        cogs_o = flt(get_costo_ventas_si(si.name))
        self.assertEqual(cogs_o, 40.0)  # COGS original vía DN de salida
        self.assertEqual(
            flt(get_costo_ventas_si(nota.name)), 0.0
        )  # la nota por sí sola no revierte

        adj = self._adj(si, nota)
        # cogs_revertido proviene EXCLUSIVAMENTE de la DN de retorno (nota sin stock).
        self.assertEqual(flt(adj["cogs_revertido"]), 40.0)
        ing_n, cogs_n, util = api._net_from_credit_notes(400.0, cogs_o, adj)
        self.assertEqual(ing_n, 0.0)
        self.assertEqual(cogs_n, 0.0)  # 40 − 40, neteado por MAT-DN de retorno
        self.assertEqual(util, 0.0)
        self.assertEqual(max(util * RATE / 100.0, 0.0), 0.0)  # comisión cero

    def test_varias_return_dn_parciales_sin_duplicar(self):
        # Una DN de salida (4 u) y DOS DN de retorno parciales (2+2): COGS revertido = 40, no 80.
        cc = self.cost_center
        dn = self._crear_dn(self.stock_item, qty=4, rate=100.0, cost_center=cc)
        si = self._si_desde_dn(dn, cc)
        self._return_dn(dn, qty=2)  # +2 u → COGS 20
        self._return_dn(dn, qty=2)  # +2 u → COGS 20
        nota = self._nota_sin_stock(si)
        cogs_o = flt(get_costo_ventas_si(si.name))
        self.assertEqual(cogs_o, 40.0)
        adj = self._adj(si, nota)
        self.assertEqual(
            flt(adj["cogs_revertido"]), 40.0
        )  # 20+20, cada DN una sola vez
        _, cogs_n, _ = api._net_from_credit_notes(400.0, cogs_o, adj)
        self.assertEqual(cogs_n, 0.0)

    def test_return_dn_cancelada_no_afecta_cogs(self):
        # Una DN de retorno CANCELADA (docstatus=2) no debe contribuir al COGS revertido.
        cc = self.cost_center
        dn = self._crear_dn(self.stock_item, qty=4, rate=100.0, cost_center=cc)
        si = self._si_desde_dn(dn, cc)
        rdn = self._return_dn(dn)
        rdn.cancel()  # queda docstatus=2
        # El helper solo netea DN de retorno docstatus=1 → 0.
        self.assertEqual(flt(api._cogs_revertido_return_dn(si.name, set())), 0.0)
        self.assertEqual(
            flt(get_costo_ventas_si(si.name)), 40.0
        )  # COGS original intacto

    def test_sin_entrega_cogs_cero(self):
        # SI update_stock=0 sin DN (nunca entregada) + nota devolución → COGS 0 y sin reverso de DN.
        cc = self.cost_center
        si = self._crear_si(
            self.stock_item, qty=2, rate=100.0, update_stock=0, cost_center=cc
        )
        self.assertEqual(
            flt(get_costo_ventas_si(si.name)), 0.0
        )  # nunca entregada → COGS 0
        self.assertEqual(
            flt(api._cogs_revertido_return_dn(si.name, set())), 0.0
        )  # sin DN de retorno
        nota = self._nota_sin_stock(si)
        adj = self._adj(si, nota)
        self.assertEqual(flt(adj["cogs_revertido"]), 0.0)
        ing_n, cogs_n, util = api._net_from_credit_notes(200.0, 0.0, adj)
        self.assertEqual(ing_n, 0.0)
        self.assertEqual(cogs_n, 0.0)
        self.assertEqual(util, 0.0)

    def test_no_inventariable_cogs_cero(self):
        # Artículo de servicio (no stock) con devolución total → COGS 0, comisión 0.
        cc = self.cost_center
        si = self._crear_si(
            self.service_item, qty=1, rate=1000.0, update_stock=0, cost_center=cc
        )
        nota = self._nota_sin_stock(si)
        self._set_outstanding(si.name, 0)
        frappe.db.set_value(
            "Sales Invoice", nota.name, "fm_factura_fiscal_mx", nota.name
        )
        with patch.object(
            api, "_ffm_tipo_map", return_value={nota.name: NOTA_CREDITO_DEVOLUCION}
        ):
            res = get_commission_rows(
                [cc], si.posting_date, si.posting_date, rates_by_cc=self._rate(cc)
            )
        r = {x["sales_invoice_id"]: x for x in res["rows"]}[si.name]
        self.assertEqual(r["cogs_original"], 0.0)
        self.assertEqual(r["cogs_revertido"], 0.0)
        self.assertEqual(r["ingreso_neto"], 0.0)
        self.assertEqual(r["total_comision"], 0.0)

    def _cuenta_descuentos(self):
        parent = frappe.db.get_value(
            "Account",
            {"company": self.company, "root_type": "Income", "is_group": 1},
            "name",
        )
        disc = f"Descuentos LLCS Test - {self.abbr}"
        if not frappe.db.exists("Account", disc):
            acc = frappe.new_doc("Account")
            acc.account_name = "Descuentos LLCS Test"
            acc.company = self.company
            acc.parent_account = parent
            acc.root_type = "Income"
            acc.insert(ignore_permissions=True)
            disc = acc.name
        return disc

    def _nota(self, si, rate, income_account=None):
        # Nota de crédito parcial sin vínculo de inventario; income_account opcional (marcador descuento).
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
            make_sales_return,
        )

        n = make_sales_return(si.name)
        n.update_stock = 0
        n.items[0].rate = rate
        for it in n.items:
            it.delivery_note = None
            it.dn_detail = None
            if income_account:
                it.income_account = income_account
        n.insert(ignore_permissions=True)
        n.submit()
        return n

    def test_flujo_completo_lote_mixto(self):
        # Flujo completo con 4 facturas simultáneas; ninguna nota detiene el lote.
        cc = self.cost_center
        disc = self._cuenta_descuentos()

        # (1) Devolución SIN FFM (servicio, parcial -300) → ingreso 700, COGS 0, com 70.
        si_dev = self._crear_si(
            self.service_item, qty=1, rate=1000.0, update_stock=0, cost_center=cc
        )
        self._nota(si_dev, rate=300.0)
        self._set_outstanding(si_dev.name, 0)

        # (2) Descuento por marcadores (stock): nota qty=-10 @ 20 = -200 → ingreso 800, COGS intacto 100.
        si_desc = self._crear_si(
            self.stock_item, qty=10, rate=100.0, update_stock=1, cost_center=cc
        )
        self._nota(
            si_desc, rate=20.0, income_account=disc
        )  # total -200 (rate ≤ original 100)
        self._set_outstanding(si_desc.name, 0)

        # (3) Devolución vía DN de retorno (flujo real SI→DN; retorno parcial 2 de 4): nota -200.
        si_dnret = self._crear_si(
            self.stock_item, qty=4, rate=100.0, update_stock=0, cost_center=cc
        )
        dn = self._entregar_si(si_dnret)  # entrega completa (COGS 40); delivered_qty=4
        self._return_dn(dn, qty=2)  # retorno parcial → COGS revertido 20
        self._nota(si_dnret, rate=50.0)  # nota -200
        self._set_outstanding(si_dnret.name, 0)

        # (4) Legacy normal SIN notas → ingreso 500, com 50.
        si_leg = self._crear_si(
            self.service_item, qty=1, rate=500.0, update_stock=0, cost_center=cc
        )
        self._set_outstanding(si_leg.name, 0)

        with (
            patch.object(api, "_ffm_tipo_map", return_value={}),
            patch.object(api, "get_cuenta_descuentos", return_value=disc),
        ):
            res = get_commission_rows(
                [cc], si_leg.posting_date, si_leg.posting_date, rates_by_cc={cc: RATE}
            )
        rows = {x["sales_invoice_id"]: x for x in res["rows"]}

        # Ninguna nota detuvo el lote: las 4 facturas atraviesan get_sales_invoices → get_commission_rows
        # (la nota SIN FFM de (1) no interrumpió el cálculo de las demás).
        for n in (si_dev.name, si_desc.name, si_dnret.name, si_leg.name):
            self.assertIn(n, rows)

        # (1) devolución sin FFM
        r = rows[si_dev.name]
        self.assertEqual(r["devoluciones_03"], -300.0)
        self.assertEqual(r["ingreso_neto"], 700.0)
        self.assertEqual(r["cogs_neto"], 0.0)
        self.assertEqual(r["total_comision"], 70.0)

        # (2) descuento por marcadores → COGS intacto
        r = rows[si_desc.name]
        self.assertEqual(r["bonificaciones_01"], -200.0)
        self.assertEqual(r["devoluciones_03"], 0.0)
        self.assertEqual(r["ingreso_neto"], 800.0)
        self.assertEqual(r["cogs_original"], 100.0)
        self.assertEqual(r["cogs_revertido"], 0.0)
        self.assertEqual(r["cogs_neto"], 100.0)
        self.assertEqual(r["total_comision"], 70.0)

        # (3) devolución vía DN de retorno (full flow) → COGS neteado parcialmente
        r = rows[si_dnret.name]
        self.assertEqual(r["ingreso_neto"], 200.0)  # 400 − 200
        self.assertEqual(r["cogs_original"], 40.0)
        self.assertEqual(r["cogs_revertido"], 20.0)  # DN de retorno (2 u)
        self.assertEqual(r["cogs_neto"], 20.0)
        self.assertEqual(r["utilidad_neta"], 180.0)
        self.assertEqual(r["total_comision"], 18.0)

        # (4) legacy normal
        r = rows[si_leg.name]
        self.assertEqual(r["ingreso_neto"], 500.0)
        self.assertEqual(r["cogs_neto"], 0.0)
        self.assertEqual(r["total_comision"], 50.0)


if __name__ == "__main__":
    unittest.main()
