# Copyright (c) 2025, Llantas CS and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ClientesSinComision(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		customer: DF.Link | None
		end_date: DF.Date | None
		motivo: DF.SmallText | None
		start_date: DF.Date | None
	# end: auto-generated types

	pass