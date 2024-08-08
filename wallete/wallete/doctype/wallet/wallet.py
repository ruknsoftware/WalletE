# Copyright (c) 2024, Hamza Abuabada and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from erpnext.accounts.utils import get_balance_on
from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import get_pos_invoices
from erpnext.selling.page.point_of_sale.point_of_sale import check_opening_entry


class Wallet(Document):
    pass


@frappe.whitelist()
def get_customer_wallet(customer, exclude_invoice=None):
    try:
        customer_wallet_doc = frappe.get_doc("Wallet", {'customer': customer})
        customer_wallet_amount = get_balance_on(
            account=customer_wallet_doc.account,
            party_type="Customer",
            party=customer_wallet_doc.customer
        )
        user = frappe.session.user
        user_opening_entry = check_opening_entry(user)[0]
        pos_invoices = get_pos_invoices(
            start=user_opening_entry.period_start_date,
            end=now_datetime(),
            pos_profile=user_opening_entry.pos_profile,
            user=user
        )

        open_pos_wallet_amount = 0.0
        if len(pos_invoices) != 0:
            for pos_invoice in pos_invoices:
                if exclude_invoice == pos_invoice.name:
                    continue
                pos_invoice_customer = frappe.get_value("POS Invoice", pos_invoice.name, 'customer')
                if pos_invoice_customer == customer:
                    wallet_amount_from_payments = get_wallet_amount_from_payments(pos_invoice.payments)
                    open_pos_wallet_amount = open_pos_wallet_amount + wallet_amount_from_payments

        return customer_wallet_amount - open_pos_wallet_amount
    except frappe.DoesNotExistError:
        return 0.0


def get_wallet_amount_from_payments(payments):
    wallet_amount = 0.0
    for payment in payments:
        payment_doc = frappe.get_doc("Mode of Payment", payment.mode_of_payment)
        if payment_doc.is_wallet_payment and payment.amount > 0.0:
            wallet_amount = wallet_amount + payment.amount

    return wallet_amount
