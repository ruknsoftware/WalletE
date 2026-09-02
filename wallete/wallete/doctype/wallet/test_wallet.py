# Copyright (c) 2024, Hamza Abuabada and Contributors
# See license.txt

import frappe
from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.mode_of_payment.test_mode_of_payment import (
	set_default_account_for_mode_of_payment,
)
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate


class TestWallet(FrappeTestCase):
	def test_wallet_is_liability_and_gl_sides(self):
		company = "_Test Company"
		cash_account = "Cash - _TC"
		wallet_account = create_account(
			account_name="Customer Wallet",
			parent_account="Current Liabilities - _TC",
			company=company,
			account_type="Receivable",
		)

		wallet = frappe.get_doc(
			{
				"doctype": "Wallet",
				"customer": "_Test Customer",
				"company": company,
				"status": "Active",
				"account": "Debtors - _TC",
			}
		)
		self.assertRaises(frappe.ValidationError, wallet.validate)

		wallet1 = _get_or_create_wallet("_Test Customer", company, wallet_account)
		wallet2 = _get_or_create_wallet("_Test Customer 1", company, wallet_account)

		set_default_account_for_mode_of_payment(
			frappe.get_doc("Mode of Payment", "Cash"), company, cash_account
		)

		payment = frappe.get_doc(
			{
				"doctype": "Wallet Entry",
				"company": company,
				"posting_date": nowdate(),
				"transaction_type": "Wallet Payment",
				"transaction_from": "Mode of Payment",
				"source_of_payment": "Cash",
				"to_wallet": wallet1,
				"amount": 1000,
			}
		).insert()
		payment.submit()

		self._assert_gl(
			payment.name,
			[
				{"account": cash_account, "debit": 1000, "credit": 0, "party": None},
				{"account": wallet_account, "debit": 0, "credit": 1000, "party": "_Test Customer"},
			],
		)

		transfer = frappe.get_doc(
			{
				"doctype": "Wallet Entry",
				"company": company,
				"posting_date": nowdate(),
				"transaction_type": "Wallet Transfer",
				"transaction_from": "Wallet",
				"source_of_payment": wallet1,
				"to_wallet": wallet2,
				"amount": 1000,
			}
		).insert()
		transfer.submit()

		self._assert_gl(
			transfer.name,
			[
				{"account": wallet_account, "debit": 1000, "credit": 0, "party": "_Test Customer"},
				{"account": wallet_account, "debit": 0, "credit": 1000, "party": "_Test Customer 1"},
			],
		)

	def _assert_gl(self, voucher_no, expected):
		rows = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Wallet Entry", "voucher_no": voucher_no, "is_cancelled": 0},
			fields=["account", "debit", "credit", "party"],
		)
		got = {(r.account, flt(r.debit), flt(r.credit), r.party or None) for r in rows}
		want = {(r["account"], flt(r["debit"]), flt(r["credit"]), r["party"]) for r in expected}
		self.assertEqual(got, want)


def _get_or_create_wallet(customer, company, account):
	name = f"{customer}-WALLET"
	if frappe.db.exists("Wallet", name):
		doc = frappe.get_doc("Wallet", name)
		doc.account = account
		doc.status = "Active"
		doc.save()
		return doc.name
	return (
		frappe.get_doc(
			{
				"doctype": "Wallet",
				"customer": customer,
				"company": company,
				"status": "Active",
				"account": account,
			}
		)
		.insert()
		.name
	)
