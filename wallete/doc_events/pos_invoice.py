from frappe import throw, _
from wallete.wallete.doctype.wallet.wallet import get_customer_wallet, get_wallet_amount_from_payments


def override_on_submit(doc, method):
    wallet_amount = get_wallet_amount_from_payments(doc.payments)
    customer_wallet = get_customer_wallet(doc.customer, doc.name)

    if wallet_amount > customer_wallet:
        throw(_("Customer Wallet Balance Must grater than or equal paid from amount"))
