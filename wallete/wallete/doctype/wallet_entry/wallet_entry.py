# Copyright (c) 2024, Hamza Abuabada and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.setup.utils import get_exchange_rate


class WalletEntry(AccountsController):
    def __init__(self, *args, **kwargs):
        super(WalletEntry, self).__init__(*args, **kwargs)

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

    def build_gl_map(self):
        accounts = [
            self.__get_account_with_transactions(self.transaction_from, self.debit_from),
            self.__get_account_with_transactions(self.transaction_to, self.credit_to),
        ]
        gl_map = []
        for idx, account in enumerate(accounts):
            debit = flt(self.amount, self.precision("amount"))
            credit = 0.0
            debit_in_account_currency = flt(self.amount, self.precision("amount"))
            credit_in_account_currency = 0.0
            if idx == 1:
                debit = 0.0
                credit = flt(self.amount, self.precision("amount"))
                debit_in_account_currency = 0.0
                credit_in_account_currency = flt(self.amount, self.precision("amount"))

            gl_map.append(
                self.get_gl_dict(
                    {
                        "account": account.name,
                        # "party_type": account_row.party_type,
                        # "party": account_row.party,
                        "debit": debit,
                        "credit": credit,
                        "account_currency": account.account_currency,
                        "debit_in_account_currency": debit_in_account_currency,
                        "credit_in_account_currency": credit_in_account_currency,
                        "cost_center": self.cost_center,
                        "project": self.project,
                    },
                    # item=account_row,
                )
            )

        return gl_map

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
