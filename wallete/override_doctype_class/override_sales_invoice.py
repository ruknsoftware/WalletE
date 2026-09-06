import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.utils import get_account_currency
from frappe.utils import cint, flt

from wallete.wallete.doctype.wallet.wallet import (
	allocate_wallet_spend,
	apply_mode_of_payment_accounts,
	is_wallet_mode_of_payment,
	restore_wallet_spend,
)


class OverrideSalesInvoice(SalesInvoice):
	def set_account_for_mode_of_payment(self):
		apply_mode_of_payment_accounts(self)

	def make_pos_gl_entries(self, gl_entries):
		# ERPNEXT CODE
		if cint(self.is_pos):

			skip_change_gl_entries = not cint(
				frappe.db.get_single_value("Accounts Settings", "post_change_gl_entries")
			)

			for payment_mode in self.payments:
				if skip_change_gl_entries and payment_mode.account == self.account_for_change_amount:
					payment_mode.base_amount -= flt(self.change_amount)

				if payment_mode.amount:
					# POS, make payment entries
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": self.debit_to,
								"party_type": "Customer",
								"party": self.customer,
								"against": payment_mode.account,
								"credit": payment_mode.base_amount,
								"credit_in_account_currency": payment_mode.base_amount
								if self.party_account_currency == self.company_currency
								else payment_mode.amount,
								"against_voucher": self.return_against
								if cint(self.is_return) and self.return_against
								else self.name,
								"against_voucher_type": self.doctype,
								"cost_center": self.cost_center,
							},
							self.party_account_currency,
							item=self,
						)
					)

					payment_mode_account_currency = get_account_currency(payment_mode.account)

					# OUR CODE
					party_type, party = self.get_party_and_party_type_for_pos_gl_entry(
						payment_mode.mode_of_payment, payment_mode.account
					)
					# ERPNEXT CODE — wallet spend is split against Wallet Entry advances
					for payment_slice in self._wallet_payment_slices(payment_mode):
						debit = payment_slice["amount"]
						debit_in_account_currency = (
							debit
							if payment_mode_account_currency == self.company_currency
							else flt(payment_mode.amount) * debit / flt(payment_mode.base_amount)
						)
						gle = {
							"account": payment_mode.account,
							"party_type": party_type,
							"party": party,
							"against": self.customer,
							"debit": debit,
							"debit_in_account_currency": debit_in_account_currency,
							"cost_center": self.cost_center,
						}
						if payment_slice.get("voucher_no"):
							gle["against_voucher_type"] = payment_slice["voucher_type"]
							gle["against_voucher"] = payment_slice["voucher_no"]
						gl_entries.append(self.get_gl_dict(gle, payment_mode_account_currency, item=self))

			if not skip_change_gl_entries:
				self.make_gle_for_change_amount(gl_entries)

	def on_cancel(self):
		restore_wallet_spend(self.doctype, self.name)
		super().on_cancel()

	def _wallet_payment_slices(self, payment_mode):
		if not is_wallet_mode_of_payment(payment_mode.mode_of_payment):
			return [{"voucher_type": None, "voucher_no": None, "amount": payment_mode.base_amount}]
		return allocate_wallet_spend(
			self.customer, payment_mode.account, payment_mode.base_amount, apply=self.docstatus == 1,
		)

	def get_party_and_party_type_for_pos_gl_entry(self, mode_of_payment, account):
		if is_wallet_mode_of_payment(mode_of_payment):
			return "Customer", self.customer
		return "", ""
