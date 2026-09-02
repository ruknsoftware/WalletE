# Copyright (c) 2024, Hamza Abuabada and contributors
# For license information, please see license.txt
import frappe
from erpnext.accounts.utils import get_balance_on
from frappe import _, throw
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull
from frappe.utils import flt


class Wallet(Document):
	def validate(self):
		account = frappe.get_doc("Account", self.account)
		if account.account_type != "Receivable" or account.root_type != "Liability":
			throw(_("Wallet Account must be a Liability (credit) account with type Receivable"))


def is_wallet_mode_of_payment(mode_of_payment):
	if not mode_of_payment:
		return False
	return bool(frappe.get_cached_value("Mode of Payment", mode_of_payment, "is_wallet_payment"))


def get_customer_wallet_account(customer):
	wallet = frappe.db.get_value(
		"Wallet", {"customer": customer}, ["name", "account", "status"], as_dict=True
	)
	if not wallet:
		throw(_("Customer {0} has no Wallet").format(customer))
	if wallet.status != "Active":
		throw(_("Wallet {0} is not active").format(wallet.name))
	return wallet.account


def apply_mode_of_payment_accounts(doc):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account

	for payment in doc.get("payments") or []:
		if not payment.mode_of_payment:
			continue
		if is_wallet_mode_of_payment(payment.mode_of_payment):
			payment.account = get_customer_wallet_account(doc.customer)
		else:
			payment.account = get_bank_cash_account(payment.mode_of_payment, doc.company).get("account")


@frappe.whitelist()
def get_customer_wallet_balance(customer: str, exclude_invoice: str | None = None):
	try:
		customer_wallet_amount = get_customer_wallet_ledger_balance(customer)
		pos_invoices = get_customer_open_pos_invoices(customer=customer, exclude_invoice=exclude_invoice)
		open_pos_wallet_amount = sum(
			get_wallet_amount_from_payments(pos_invoice.payments) for pos_invoice in pos_invoices
		)
		return customer_wallet_amount - open_pos_wallet_amount
	except frappe.DoesNotExistError:
		return 0.0


def get_customer_wallet_ledger_balance(customer):
	customer_wallet_doc = frappe.get_doc("Wallet", {"customer": customer})
	customer_wallet_amount = get_balance_on(
		account=customer_wallet_doc.account, party_type="Customer", party=customer_wallet_doc.customer,
	)
	# get_balance_on is debit - credit; liability wallets hold a credit balance
	if frappe.get_cached_value("Account", customer_wallet_doc.account, "root_type") == "Liability":
		customer_wallet_amount = -flt(customer_wallet_amount)
	return customer_wallet_amount


def get_wallet_amount_from_payments(payments):
	wallet_amount = 0.0
	for payment in payments:
		payment_doc = frappe.get_doc("Mode of Payment", payment.mode_of_payment)
		if payment_doc.is_wallet_payment:
			wallet_amount = wallet_amount + payment.amount

	return wallet_amount


def get_customer_open_pos_invoices(customer, exclude_invoice=None):
	pos_invoice = DocType("POS Invoice")
	query = (
		frappe.qb.from_(pos_invoice)
		.select(pos_invoice.name)
		.where(
			(pos_invoice.docstatus == 1)
			& (IfNull(pos_invoice.consolidated_invoice, "") == "")
			& (pos_invoice.customer == customer)
		)
	)
	if exclude_invoice:
		query = query.where((pos_invoice.name != exclude_invoice))

	data = query.run(as_dict=True)

	data = [frappe.get_doc("POS Invoice", d["name"]).as_dict() for d in data]

	return data
