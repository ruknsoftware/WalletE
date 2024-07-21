# Copyright (c) 2024, Hamza Abuabada and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw, ValidationError
from frappe.utils import flt
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries


class WalletEntry(AccountsController):

    def __init__(self, *args, **kwargs):
        super(WalletEntry, self).__init__(*args, **kwargs)

    def validate(self):
        self.check_duplicated_wallet()
        if self.transaction_type == "Wallet Transfer":
            self.__check_wallet_activation(self.source_of_payment)
        self.__check_wallet_activation(self.to_wallet)
        if self.transaction_type == "Wallet Payment" and not self.__get_mode_of_payment_account():
            throw(_(f"Mode Of Payment {self.source_of_payment} must have {self.company} account"))

    def check_duplicated_wallet(self):
        if self.transaction_type == "Wallet Transfer":
            if self.source_of_payment == self.to_wallet:
                throw(_(f"Mode Of Payment {self.source_of_payment} cant be equal Wallet {self.to_wallet}"))

    def __check_wallet_activation(self, wallet):
        if frappe.get_value("Wallet", wallet, "status") != "Active":
            throw(_(f"Wallet {wallet} is not active"))

    def on_submit(self):
        self.make_gl_entries_for_wallet_entry()

    def __get_wallet_account(self, wallet_name):
        wallet_account = frappe.get_doc("Wallet", wallet_name).account
        return frappe.get_doc("Account", wallet_account)

    def __get_mode_of_payment_account(self):
        mode_of_payment = frappe.get_doc("Mode of Payment", self.source_of_payment)
        account = ""
        for account in mode_of_payment.accounts:
            if account.company == self.company:
                account = account.default_account
                break
        return account

    def __get_party_from_transactions(self, transaction_type, transaction):
        party_type, party = "", ""
        if transaction_type == "Wallet":
            party_type = "Customer"
            party = frappe.get_value(transaction_type, transaction, "customer")

        return party_type, party

    def build_gl_map(self):
        if self.transaction_type == "Wallet Transfer":
            source_of_payment_account = self.__get_wallet_account(self.source_of_payment)
        elif self.transaction_type == "Wallet Payment":
            source_of_payment_account = frappe.get_doc("Account", self.__get_mode_of_payment_account())
        else:
            throw(_(f"UNKNOWN Transaction type {self.transaction_type}"))
        return [
            self.__make_gl_row(
                transaction_from=self.transaction_from,
                transaction=self.source_of_payment,
                account=source_of_payment_account,
                credit=self.amount
            ),
            self.__make_gl_row(
                transaction_from="Wallet",
                transaction=self.to_wallet,
                account=self.__get_wallet_account(self.to_wallet),
                debit=self.amount
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
                },
                item=account,
            )

    def make_gl_entries_for_wallet_entry(self, cancel=0, adv_adj=0):
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
