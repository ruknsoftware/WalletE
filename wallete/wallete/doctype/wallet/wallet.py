# Copyright (c) 2024, Hamza Abuabada and contributors
# For license information, please see license.txt
import frappe
from frappe import throw, _
from frappe.model.document import Document
from erpnext.accounts.utils import get_balance_on
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull


class Wallet(Document):
    def validate(self):
        account = frappe.get_doc("Account", self.account)
        if account.account_type != "Receivable":
            throw(_("Wallet Account Type must be Receivable account"))


@frappe.whitelist()
def get_customer_wallet_balance(customer, exclude_invoice=None):
    try:
        customer_wallet_doc = frappe.get_doc("Wallet", {'customer': customer})
        customer_wallet_amount = get_balance_on(
            account=customer_wallet_doc.account,
            party_type="Customer",
            party=customer_wallet_doc.customer
        )

        pos_invoices = get_customer_open_pos_invoices(
            customer=customer,
            exclude_invoice=exclude_invoice
        )

        open_pos_wallet_amount = 0.0
        if len(pos_invoices) != 0:
            for pos_invoice in pos_invoices:
                wallet_amount_from_payments = get_wallet_amount_from_payments(pos_invoice.payments)
                open_pos_wallet_amount = open_pos_wallet_amount + wallet_amount_from_payments

        return customer_wallet_amount - open_pos_wallet_amount
    except frappe.DoesNotExistError:
        return 0.0


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
            (pos_invoice.docstatus == 1) &
            (IfNull(pos_invoice.consolidated_invoice, "") == "") &
            (pos_invoice.customer == customer)
        )
    )
    if exclude_invoice:
        query = query.where((pos_invoice.name != exclude_invoice))

    data = query.run(as_dict=True)

    data = [frappe.get_doc("POS Invoice", d["name"]).as_dict() for d in data]

    return data
