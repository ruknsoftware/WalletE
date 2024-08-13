# Copyright (c) 2024, Hamza Abuabada and contributors
# For license information, please see license.txt
import frappe
from frappe import throw, _
from frappe.model.document import Document
from erpnext.accounts.utils import get_balance_on


class Wallet(Document):
    def validate(self):
        account = frappe.get_doc("Account", self.account)
        if account.account_type != "Receivable":
            throw(_("Wallet Account Type must be Receivable account"))


@frappe.whitelist()
def get_customer_wallet(customer, exclude_invoice):
    try:
        customer_wallet_doc = frappe.get_doc("Wallet", {'customer': customer})
        customer_wallet_amount = get_balance_on(
            account=customer_wallet_doc.account,
            party_type="Customer",
            party=customer_wallet_doc.customer
        )

        pos_invoices = get_customer_open_pos_invoice(
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
        if payment_doc.is_wallet_payment and payment.amount > 0.0:
            wallet_amount = wallet_amount + payment.amount

    return wallet_amount


def get_customer_open_pos_invoice(customer, exclude_invoice):
    data = frappe.db.sql(
        """
    select
        name, timestamp(posting_date, posting_time) as "timestamp"
    from
        `tabPOS Invoice`
    where
        docstatus = 1 and ifnull(consolidated_invoice,'') = '' and customer = %s and name != %s
    """,
        (customer, exclude_invoice),
        as_dict=1,
    )
    data = [frappe.get_doc("POS Invoice", d.name).as_dict() for d in data]

    return data
