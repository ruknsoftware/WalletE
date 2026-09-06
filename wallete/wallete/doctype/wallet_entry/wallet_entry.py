# Copyright (c) 2024, Hamza Abuabada and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from frappe import _, throw
from frappe.utils import flt

from wallete.wallete.doctype.wallet.wallet import allocate_wallet_spend, restore_wallet_spend


class WalletEntry(AccountsController):
	def __init__(self, *args, **kwargs):
		super(WalletEntry, self).__init__(*args, **kwargs)

	def validate(self):
		self.check_duplicated_wallet()
		if self.transaction_type == "Wallet Transfer":
			self.__check_wallet_activation(self.source_of_payment)
		self.__check_wallet_activation(self.to_wallet)
		if self.transaction_type == "Wallet Payment" and not self.__get_mode_of_payment_account():
			throw(
				_("Mode Of Payment {0} must have {1} account").format(self.source_of_payment, self.company)
			)

	def check_duplicated_wallet(self):
		if self.transaction_type == "Wallet Transfer":
			if self.source_of_payment == self.to_wallet:
				throw(
					_("Mode Of Payment {0} can't be equal Wallet {1}").format(
						self.source_of_payment, self.to_wallet
					)
				)

	def __check_wallet_activation(self, wallet):
		if frappe.get_value("Wallet", wallet, "status") != "Active":
			throw(_("Wallet {0} is not active").format(wallet))

	def on_submit(self):
		self.make_gl_entries_for_wallet_entry()
		self.db_set("outstanding_amount", self.amount)

	def on_cancel(self):
		restore_wallet_spend(self.doctype, self.name)
		super().on_cancel()
		self.make_gl_entries_for_wallet_entry(cancel=1)
		self.db_set("outstanding_amount", 0)

	def __get_wallet_account(self, wallet_name):
		wallet_account = frappe.get_doc("Wallet", wallet_name).account
		return frappe.get_doc("Account", wallet_account)

	def __get_mode_of_payment_account(self):
		mode_of_payment = frappe.get_doc("Mode of Payment", self.source_of_payment)
		for row in mode_of_payment.accounts:
			if row.company == self.company:
				return row.default_account
		return None

	def __get_party_from_transactions(self, transaction_type, transaction):
		party_type, party = "", ""
		if transaction_type == "Wallet":
			party_type = "Customer"
			party = frappe.get_value(transaction_type, transaction, "customer")

		return party_type, party

	def build_gl_map(self):
		dest_account = self.__get_wallet_account(self.to_wallet)
		dest_row = self.__make_gl_row(
			transaction_from="Wallet",
			transaction=self.to_wallet,
			account=dest_account,
			credit=self.amount,
			against_voucher_type=self.doctype,
			against_voucher=self.name,
		)
		if self.transaction_type == "Wallet Transfer":
			source_account = self.__get_wallet_account(self.source_of_payment)
			source_customer = frappe.db.get_value("Wallet", self.source_of_payment, "customer")
			rows = []
			for payment_slice in allocate_wallet_spend(
				source_customer,
				source_account.name,
				self.amount,
				apply=self.docstatus == 1,
			):
				rows.append(
					self.__make_gl_row(
						transaction_from=self.transaction_from,
						transaction=self.source_of_payment,
						account=source_account,
						debit=payment_slice["amount"],
						against_voucher_type=payment_slice.get("voucher_type"),
						against_voucher=payment_slice.get("voucher_no"),
					)
				)
			rows.append(dest_row)
			return rows
		if self.transaction_type == "Wallet Payment":
			source_account = frappe.get_doc("Account", self.__get_mode_of_payment_account())
			return [
				self.__make_gl_row(
					transaction_from=self.transaction_from,
					transaction=self.source_of_payment,
					account=source_account,
					debit=self.amount,
				),
				dest_row,
			]
		throw(_("UNKNOWN Transaction type {0}").format(self.transaction_type))

	def __make_gl_row(
		self,
		transaction_from,
		transaction,
		account,
		debit=0.0,
		credit=0.0,
		against_voucher_type=None,
		against_voucher=None,
	):
		party_type, party = self.__get_party_from_transactions(transaction_from, transaction)
		if debit:
			debit = flt(debit, self.precision("amount"))
			credit = 0.0
		else:
			debit = 0.0
			credit = flt(credit, self.precision("amount"))

		args = {
			"account": account.name,
			"party_type": party_type,
			"party": party,
			"debit": debit,
			"credit": credit,
			"account_currency": account.account_currency,
			"debit_in_account_currency": debit,
			"credit_in_account_currency": credit,
			"cost_center": self.cost_center,
		}
		if against_voucher:
			args["against_voucher_type"] = against_voucher_type
			args["against_voucher"] = against_voucher
		return self.get_gl_dict(args, item=account)

	def make_gl_entries_for_wallet_entry(self, cancel=0, adv_adj=0):
		if cancel:
			make_reverse_gl_entries(
				voucher_type=self.doctype,
				voucher_no=self.name,
				adv_adj=adv_adj,
				update_outstanding="Yes",
			)
			return

		merge_entries = frappe.db.get_single_value("Accounts Settings", "merge_similar_account_heads")
		gl_map = self.build_gl_map()
		if gl_map:
			make_gl_entries(
				gl_map, cancel=0, adv_adj=adv_adj, merge_entries=merge_entries, update_outstanding="Yes",
			)
