import frappe
from frappe import throw, _
from wallete.wallete.doctype.wallet.wallet import get_customer_wallet_balance


def check_customer_wallet_account(doc, method):
    if doc.party_type == "Customer" and doc.party:
        customer_wallet_account = frappe.get_value("Wallet", {'customer': doc.party}, 'account')

        if doc.account == customer_wallet_account:
            customer_wallet = get_customer_wallet_balance(customer=doc.party)
            if customer_wallet < 0:
                throw(_("Wallet account for a customer not allowed to be less than zero"))
