# Copyright (c) 2026, Consultoria en Negocios y Aplicaciones and Contributors
# See license.txt
"""Tests del ajuste de comisiones por notas de crédito (motivo 01 y 03).

Alcance de esta iteración: facturas originales liquidadas (docstatus=1, is_return=0,
outstanding_amount=0) mediante combinación de Payment Entry + una o más notas de crédito,
que ERPNext marca "Credit Note Issued" y por eso quedaban excluidas del esquema de comisiones.

Estos tests son PUROS + MOCKEADOS: no requieren tablas fiscales ni facturacion_mexico
instalado en el sitio de pruebas. Validan:
  - la aritmética neta consolidada (_net_from_credit_notes), y
  - la agregación/clasificación batch por evidencia documental (_build_credit_note_adjustments):
    motivo FFM → marcadores de descuento → por defecto devolución (nunca detiene el cálculo).
"""

import unittest
from unittest.mock import patch

import frappe

from llantascs_customs.llantascs_customs import api
from llantascs_customs.llantascs_customs.api import (
    NOTA_CREDITO_DESCUENTO,
    NOTA_CREDITO_DEVOLUCION,
    _build_credit_note_adjustments,
    _net_from_credit_notes,
)


class TestNetFromCreditNotes(unittest.TestCase):
    """Aritmética pura del cálculo neto (respeta signos reales: las notas vienen negativas)."""

    def test_caso1_sin_notas_conserva_original(self):
        # Factura pagada 100% con Payment Entry, sin nota de crédito → nets == originales.
        ing, cogs, util = _net_from_credit_notes(1000.0, 600.0, {})
        self.assertEqual(ing, 1000.0)
        self.assertEqual(cogs, 600.0)
        self.assertEqual(util, 400.0)

    def test_caso2_motivo01_reduce_ingreso_mantiene_cogs(self):
        # Descuento/bonificación de 200 (nota base_net_total = -200). COGS intacto.
        adj = {"bonif_01": -200.0, "dev_03": 0.0, "cogs_revertido": 0.0}
        ing, cogs, util = _net_from_credit_notes(1000.0, 600.0, adj)
        self.assertEqual(ing, 800.0)
        self.assertEqual(cogs, 600.0)  # NO se toca el costo
        self.assertEqual(util, 200.0)

    def test_caso3_motivo03_reduce_ingreso_y_cogs(self):
        # Devolución: nota base_net_total = -300, costo revertido = 180.
        adj = {"bonif_01": 0.0, "dev_03": -300.0, "cogs_revertido": 180.0}
        ing, cogs, util = _net_from_credit_notes(1000.0, 600.0, adj)
        self.assertEqual(ing, 700.0)
        self.assertEqual(cogs, 420.0)
        self.assertEqual(util, 280.0)

    def test_caso7_devolucion_total_utilidad_cero(self):
        # Devolución total: ingreso y costo se revierten por completo → utilidad neta 0.
        adj = {"bonif_01": 0.0, "dev_03": -1000.0, "cogs_revertido": 600.0}
        ing, cogs, util = _net_from_credit_notes(1000.0, 600.0, adj)
        self.assertEqual(ing, 0.0)
        self.assertEqual(cogs, 0.0)
        self.assertEqual(util, 0.0)

    def test_mixto_01_y_03_en_misma_factura(self):
        # Nota 01 (-100) + nota 03 (-300, costo revertido 180) sobre la misma factura.
        adj = {"bonif_01": -100.0, "dev_03": -300.0, "cogs_revertido": 180.0}
        ing, cogs, util = _net_from_credit_notes(1000.0, 600.0, adj)
        self.assertEqual(ing, 600.0)  # 1000 - 100 - 300
        self.assertEqual(cogs, 420.0)  # 600 - 180
        self.assertEqual(util, 180.0)


class TestBuildCreditNoteAdjustments(unittest.TestCase):
    """Agregación batch y clasificación por marcador fiscal (mockeando el acceso a BD)."""

    def _patch_db(self, notas, ffm_tipos, cogs_map=None):
        """Configura mocks para frappe.get_all y get_costo_ventas_si.

        notas: lista de dicts (name, return_against, base_net_total, fm_factura_fiscal_mx).
        ffm_tipos: dict {ffm_name: fm_tipo_nota_credito}.
        cogs_map: dict {nota_name: cogs} para get_costo_ventas_si (motivo 03).
        """
        cogs_map = cogs_map or {}

        def fake_get_all(doctype, filters=None, fields=None, **kwargs):
            if doctype == "Sales Invoice":
                self.captured_si_filters = filters
                return [frappe._dict(n) for n in notas]
            if doctype == "Factura Fiscal Mexico":
                names = filters["name"][1]
                return [
                    frappe._dict({"name": k, "fm_tipo_nota_credito": v})
                    for k, v in ffm_tipos.items()
                    if k in names
                ]
            return []

        def fake_cogs(nota_name):
            return cogs_map.get(nota_name, 0.0)

        return fake_get_all, fake_cogs

    def test_caso1_sin_notas_devuelve_vacio(self):
        with patch.object(api.frappe, "get_all", return_value=[]):
            out = _build_credit_note_adjustments(["FAC-001"])
        self.assertEqual(out, {})

    def test_lista_vacia_devuelve_vacio_sin_consultar(self):
        # No debe consultar BD si no hay facturas.
        self.assertEqual(_build_credit_note_adjustments([]), {})

    def test_caso2_motivo01_acumula_bonificacion(self):
        notas = [
            {
                "name": "NC-01",
                "return_against": "FAC-001",
                "base_net_total": -200.0,
                "fm_factura_fiscal_mx": "FFM-01",
            }
        ]
        fga, fcogs = self._patch_db(notas, {"FFM-01": NOTA_CREDITO_DESCUENTO})
        with (
            patch.object(api.frappe, "get_all", side_effect=fga),
            patch.object(api, "get_costo_ventas_si", side_effect=fcogs),
        ):
            out = _build_credit_note_adjustments(["FAC-001"])
        self.assertEqual(out["FAC-001"]["bonif_01"], -200.0)
        self.assertEqual(out["FAC-001"]["dev_03"], 0.0)
        self.assertEqual(out["FAC-001"]["cogs_revertido"], 0.0)

    def test_caso3_motivo03_revierte_cogs(self):
        notas = [
            {
                "name": "NC-03",
                "return_against": "FAC-002",
                "base_net_total": -300.0,
                "fm_factura_fiscal_mx": "FFM-03",
            }
        ]
        fga, fcogs = self._patch_db(
            notas, {"FFM-03": NOTA_CREDITO_DEVOLUCION}, cogs_map={"NC-03": 180.0}
        )
        with (
            patch.object(api.frappe, "get_all", side_effect=fga),
            patch.object(api, "get_costo_ventas_si", side_effect=fcogs),
        ):
            out = _build_credit_note_adjustments(["FAC-002"])
        self.assertEqual(out["FAC-002"]["dev_03"], -300.0)
        self.assertEqual(out["FAC-002"]["cogs_revertido"], 180.0)
        self.assertEqual(out["FAC-002"]["bonif_01"], 0.0)

    def test_caso5_varias_notas_parciales_acumulan_sin_duplicar(self):
        # Dos notas 01 y una 03 contra la MISMA factura.
        notas = [
            {
                "name": "NC-A",
                "return_against": "FAC-003",
                "base_net_total": -100.0,
                "fm_factura_fiscal_mx": "FFM-A",
            },
            {
                "name": "NC-B",
                "return_against": "FAC-003",
                "base_net_total": -150.0,
                "fm_factura_fiscal_mx": "FFM-B",
            },
            {
                "name": "NC-C",
                "return_against": "FAC-003",
                "base_net_total": -200.0,
                "fm_factura_fiscal_mx": "FFM-C",
            },
        ]
        ffm = {
            "FFM-A": NOTA_CREDITO_DESCUENTO,
            "FFM-B": NOTA_CREDITO_DESCUENTO,
            "FFM-C": NOTA_CREDITO_DEVOLUCION,
        }
        fga, fcogs = self._patch_db(notas, ffm, cogs_map={"NC-C": 120.0})
        with (
            patch.object(api.frappe, "get_all", side_effect=fga),
            patch.object(api, "get_costo_ventas_si", side_effect=fcogs),
        ):
            out = _build_credit_note_adjustments(["FAC-003"])
        self.assertEqual(out["FAC-003"]["bonif_01"], -250.0)  # -100 + -150
        self.assertEqual(out["FAC-003"]["dev_03"], -200.0)
        self.assertEqual(out["FAC-003"]["cogs_revertido"], 120.0)

    def test_caso6_notas_canceladas_excluidas_por_filtro_docstatus(self):
        # El filtro debe exigir docstatus=1 e is_return=1 (canceladas/borrador quedan fuera).
        notas = [
            {
                "name": "NC-01",
                "return_against": "FAC-004",
                "base_net_total": -50.0,
                "fm_factura_fiscal_mx": "FFM-01",
            }
        ]
        fga, fcogs = self._patch_db(notas, {"FFM-01": NOTA_CREDITO_DESCUENTO})
        with (
            patch.object(api.frappe, "get_all", side_effect=fga),
            patch.object(api, "get_costo_ventas_si", side_effect=fcogs),
        ):
            _build_credit_note_adjustments(["FAC-004"])
        self.assertEqual(self.captured_si_filters["docstatus"], 1)
        self.assertEqual(self.captured_si_filters["is_return"], 1)

    def test_sin_ffm_ni_descuento_se_trata_como_devolucion(self):
        # Nota sin FFM y sin marcadores de descuento → NO detiene el cálculo; se trata como
        # devolución y el COGS revertido se mide del inventario (aquí 0).
        notas = [
            {
                "name": "NC-X",
                "return_against": "FAC-005",
                "base_net_total": -100.0,
                "fm_factura_fiscal_mx": None,
            }
        ]
        fga, fcogs = self._patch_db(notas, {})
        with (
            patch.object(api.frappe, "get_all", side_effect=fga),
            patch.object(api, "get_costo_ventas_si", side_effect=fcogs),
            patch.object(api, "_es_descuento_persistente", return_value=False),
        ):
            out = _build_credit_note_adjustments(["FAC-005"])
        self.assertEqual(out["FAC-005"]["dev_03"], -100.0)
        self.assertEqual(out["FAC-005"]["bonif_01"], 0.0)
        self.assertEqual(out["FAC-005"]["cogs_revertido"], 0.0)

    def test_sin_ffm_con_marcadores_descuento_es_bonificacion(self):
        # Nota sin FFM pero con marcadores persistentes de la acción de descuento → motivo 01.
        notas = [
            {
                "name": "NC-D",
                "return_against": "FAC-006",
                "base_net_total": -80.0,
                "fm_factura_fiscal_mx": None,
            }
        ]
        fga, fcogs = self._patch_db(notas, {})
        with (
            patch.object(api.frappe, "get_all", side_effect=fga),
            patch.object(api, "get_costo_ventas_si", side_effect=fcogs),
            patch.object(api, "_es_descuento_persistente", return_value=True),
        ):
            out = _build_credit_note_adjustments(["FAC-006"])
        self.assertEqual(out["FAC-006"]["bonif_01"], -80.0)
        self.assertEqual(out["FAC-006"]["dev_03"], 0.0)
        self.assertEqual(
            out["FAC-006"]["cogs_revertido"], 0.0
        )  # descuento no revierte COGS


class TestSinDependenciaFacturacion(unittest.TestCase):
    """facturacion_mexico es OPCIONAL: sin la app, el módulo importa y degrada sin fallar."""

    def test_import_sin_facturacion_mexico_usa_fallbacks(self):
        # Simula la ausencia de facturacion_mexico y recarga api: no debe fallar por ImportError
        # y los helpers fiscales quedan como fallbacks seguros.
        import importlib
        import sys

        modns = "llantascs_customs.llantascs_customs.api"

        def _es_fm(k):
            return k == "facturacion_mexico" or k.startswith("facturacion_mexico.")

        saved = {k: v for k, v in list(sys.modules.items()) if _es_fm(k)}
        try:
            for k in list(sys.modules):
                if _es_fm(k):
                    sys.modules[k] = None  # fuerza ImportError en el import
            reloaded = importlib.reload(sys.modules[modns])
            self.assertIsNone(reloaded.get_cuenta_descuentos("X"))
            self.assertIsNone(reloaded.get_invoice_uuid("X"))
            self.assertFalse(reloaded.credit_note_lines_use_discount_account("X", "Y"))
        finally:
            for k in list(sys.modules):
                if _es_fm(k):
                    del sys.modules[k]
            sys.modules.update(saved)
            importlib.reload(sys.modules[modns])  # restaurar el import real

    def test_es_descuento_degrada_si_falla_evidencia_fiscal(self):
        # Si un helper fiscal falla (doctype/campo ausente), _es_descuento_persistente no revienta:
        # devuelve False y el cálculo sigue tratando la nota como devolución.
        fake = frappe._dict({"update_stock": 0, "company": "X"})

        def boom(*a, **k):
            raise RuntimeError("Facturacion Mexico Company Settings ausente")

        with (
            patch.object(api.frappe, "get_doc", return_value=fake),
            patch.object(api, "get_cuenta_descuentos", side_effect=boom),
        ):
            self.assertFalse(api._es_descuento_persistente("NC-Z"))


if __name__ == "__main__":
    unittest.main()
