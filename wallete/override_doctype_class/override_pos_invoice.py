from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice

from wallete.wallete.doctype.wallet.wallet import apply_mode_of_payment_accounts


class OverridePOSInvoice(POSInvoice):
	def set_account_for_mode_of_payment(self):
		apply_mode_of_payment_accounts(self)
