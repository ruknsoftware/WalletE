# Copyright (c) 2024, Hamza Abuabada and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.utils import flt
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries


class WalletEntry(AccountsController):

    def __init__(self, *args, **kwargs):
        super(WalletEntry, self).__init__(*args, **kwargs)

    def validate(self):
        self.check_duplicated_wallet()

    def check_duplicated_wallet(self):
        if self.transaction_type == "Wallet Transfer":
            if self.mode_of_payment == self.to_wallet:
                throw(_(f"Mode Of Payment {self.mode_of_payment} cant be equal Wallet {self.to_wallet}"))

    def on_submit(self):
        self.make_gl_entries()

    def __get_account_with_transactions(self, transaction_type, transaction):
        transaction_doc = frappe.get_doc(transaction_type, transaction)
        if transaction_type == "Wallet":
            account = transaction_doc.account
        else:
            for account in transaction_doc.accounts:
                if account.company == self.company:
                    account = account.default_account
                    break
        return frappe.get_doc("Account", account)

    def __get_party_from_transactions(self, transaction_type, transaction):
        party_type, party = "", ""
        if transaction_type == "Wallet":
            party_type = "Customer"
            party = frappe.get_value(transaction_type, transaction, "customer")

        return party_type, party

    def build_gl_map(self):
        return [
            self.__make_gl_row(
                transaction_from=self.transaction_from,
                transaction=self.mode_of_payment,
                account=self.__get_account_with_transactions(self.transaction_from, self.mode_of_payment),
                debit=self.amount
            ),
            self.__make_gl_row(
                transaction_from="Wallet",
                transaction=self.to_wallet,
                account=self.__get_account_with_transactions("Wallet", self.to_wallet),
                credit=self.amount
            )
        ]

    def __make_gl_row(self, transaction_from, transaction, account, debit=0.0, credit=0.0):
        party_type, party = self.__get_party_from_transactions(transaction_from, transaction)

        if debit != 0.0:
            debit = flt(self.amount, self.precision("amount"))
            credit = 0.0

        if credit != 0.0:
            debit = 0.0
            credit = flt(self.amount, self.precision("amount"))

        return self.get_gl_dict(
                {
                    "account": account.name,
                    "party_type": party_type,
                    "party": party,
                    "debit": debit,
                    "credit": credit,
                    "account_currency": account.account_currency,
                    "debit_in_account_currency": debit,
                    "credit_in_account_currency": credit,
                    "cost_center": self.cost_center,
                    "project": self.project,
                },
                item=account,
            )

    def make_gl_entries(self, cancel=0, adv_adj=0):
        merge_entries = frappe.db.get_single_value("Accounts Settings", "merge_similar_account_heads")

        gl_map = self.build_gl_map()

        if gl_map:
            make_gl_entries(
                gl_map,
                cancel=cancel,
                adv_adj=adv_adj,
                merge_entries=merge_entries,
                update_outstanding="Yes",
            )
