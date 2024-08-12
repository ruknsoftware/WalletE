import frappe
from frappe import throw, _
from erpnext.accounts.utils import get_balance_on


def check_customer_wallet_account(doc, method):
    if doc.party_type == "Customer" and doc.party:
        customer_wallet_account = frappe.get_value("Wallet", {'customer': doc.party}, 'account')

        if doc.account == customer_wallet_account:
            customer_wallet = get_balance_on(
                account=doc.account,
                party_type="Customer",
                party=doc.party
            )
            if customer_wallet < 0:
                throw(_("Wallet account for a customer not allowed to be less than zero"))
