# -*- coding: utf-8 -*-
"""
Llantascs Customs - Bench CLI Commands
"""

import click
import json
import frappe
from frappe.commands import pass_context


@click.group("llantascs-customs")
def llantascs_customs_group():
    """Comandos de Llantascs Customs"""
    pass


@llantascs_customs_group.command("install-cockpit")
@click.option("--company", required=True, help="Nombre de Company por defecto")
@click.option("--branch", default=None, help="Branch filtro por defecto (opcional)")
@click.option("--roles-json", default=None, help="Override de roles por workspace (JSON)")
@click.option("--only", default=None, help="Bundle específico: dg|cfo|admin|sucursal (opcional)")
@pass_context
def install_cockpit(ctx, company, branch, roles_json, only):
    """
    Crea/actualiza Cockpit 100% nativo (Number Cards, Dashboard Charts, Workspaces)

    Ejemplo:
        bench --site llantascs.dev llantascs-customs install-cockpit --company "Llantas de Calidad Star"
        bench --site llantascs.dev llantascs-customs install-cockpit --company "Llantas de Calidad Star" --only dg
    """
    from llantascs_customs.cockpit import install

    roles_override = json.loads(roles_json) if roles_json else None

    frappe.init(site=ctx.sites[0])
    frappe.connect()

    install.run(company=company, branch=branch, roles_override=roles_override, only=only)

    click.echo("✅ Cockpit instalado/actualizado correctamente.")


commands = [llantascs_customs_group]
