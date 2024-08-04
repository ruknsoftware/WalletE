# Copyright (c) 2024, Hamza Abuabada and contributors
# For license information, please see license.txt
import frappe
# import frappe
from frappe.model.document import Document
from erpnext.accounts.utils import get_balance_on


class Wallet(Document):
	pass


@frappe.whitelist()
def get_customer_wallet(customer):
	try:
		customer_wallet = frappe.get_doc("Wallet", {'customer': customer})
		return get_balance_on(
			account=customer_wallet.account,
			party_type="Customer",
			party=customer_wallet.customer
		)
	except frappe.DoesNotExistError:
		return 0.0

