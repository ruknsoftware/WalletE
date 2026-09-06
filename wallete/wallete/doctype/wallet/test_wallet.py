# Copyright (c) 2024, Hamza Abuabada and Contributors
# See license.txt

import frappe
from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.mode_of_payment.test_mode_of_payment import (
	set_default_account_for_mode_of_payment,
)
from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import (
	make_closing_entry_from_opening,
)
from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice
from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.stock.doctype.item.test_item import make_item
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate


class TestWallet(FrappeTestCase):
	def test_wallet_is_liability_and_gl_sides(self):
		company, cash_account, wallet_account = _company_accounts()
		self.assertRaises(
			frappe.ValidationError,
			frappe.get_doc(
				{
					"doctype": "Wallet",
					"customer": "_Test Customer",
					"company": company,
					"status": "Active",
					"account": "Debtors - _TC",
				}
			).validate,
		)

		source = _ensure_customer("_Test Wallet Liability Source")
		dest = _ensure_customer("_Test Wallet Liability Dest")
		wallet1 = _get_or_create_wallet(source, company, wallet_account)
		wallet2 = _get_or_create_wallet(dest, company, wallet_account)
		set_default_account_for_mode_of_payment(
			frappe.get_doc("Mode of Payment", "Cash"), company, cash_account
		)

		payment = _make_wallet_entry(company, "Wallet Payment", "Mode of Payment", "Cash", wallet1, 1000)
		self._assert_gl(
			"Wallet Entry",
			payment.name,
			[
				{"account": cash_account, "debit": 1000, "credit": 0, "party": None},
				{"account": wallet_account, "debit": 0, "credit": 1000, "party": source},
			],
		)

		transfer = _make_wallet_entry(company, "Wallet Transfer", "Wallet", wallet1, wallet2, 1000)
		self._assert_gl(
			"Wallet Entry",
			transfer.name,
			[
				{"account": wallet_account, "debit": 1000, "credit": 0, "party": source},
				{"account": wallet_account, "debit": 0, "credit": 1000, "party": dest},
			],
		)
		payment.reload()
		self.assertEqual(flt(payment.outstanding_amount), 0)
		transfer.reload()
		self.assertEqual(flt(transfer.outstanding_amount), 1000)
		self._assert_wallet_debit_against("Wallet Entry", transfer.name, wallet_account, payment.name)
		transfer.cancel()
		payment.reload()
		transfer.reload()
		self.assertEqual(flt(payment.outstanding_amount), 1000)
		self.assertEqual(flt(transfer.outstanding_amount), 0)

	def test_pos_invoice_wallet_payment_account(self):
		company, cash_account, wallet_account = _company_accounts()
		wallet = _get_or_create_wallet("_Test Customer", company, wallet_account)
		mop = _get_or_create_wallet_mop(company, cash_account)
		topup = _make_wallet_entry(company, "Wallet Payment", "Mode of Payment", "Cash", wallet, 100)
		item = _ensure_pos_item()

		pos_profile = make_pos_profile()
		pos_profile.append("payments", {"mode_of_payment": mop})
		pos_profile.save()
		opening = create_opening_entry(pos_profile, frappe.session.user)

		pos = create_pos_invoice(
			item=item, qty=1, rate=100, update_stock=0, pos_profile=pos_profile.name, do_not_save=1,
		)
		pos.set("payments", [])
		pos.append("payments", {"mode_of_payment": mop, "amount": 100})
		pos.insert()
		self.assertEqual(pos.payments[0].account, wallet_account)
		pos.submit()

		closing = make_closing_entry_from_opening(opening)
		for row in closing.payment_reconciliation:
			row.closing_amount = row.expected_amount
		closing.submit()

		pos.reload()
		self.assertTrue(pos.consolidated_invoice)
		self._assert_gl_contains(
			"Sales Invoice",
			pos.consolidated_invoice,
			[
				{"account": wallet_account, "debit": 100, "credit": 0, "party": "_Test Customer"},
				{"account": "Sales - _TC", "debit": 0, "credit": 100, "party": None},
			],
		)
		cash_debit = sum(
			flt(r.debit)
			for r in frappe.get_all(
				"GL Entry",
				filters={
					"voucher_type": "Sales Invoice",
					"voucher_no": pos.consolidated_invoice,
					"is_cancelled": 0,
				},
				fields=["account", "debit"],
			)
			if r.account == cash_account
		)
		self.assertEqual(cash_debit, 0)
		topup.reload()
		self.assertEqual(flt(topup.outstanding_amount), 0)
		self._assert_wallet_debit_against(
			"Sales Invoice", pos.consolidated_invoice, wallet_account, topup.name
		)

	def test_sales_invoice_wallet_payment_gl_sides(self):
		company, cash_account, wallet_account = _company_accounts()
		wallet = _get_or_create_wallet("_Test Customer", company, wallet_account)
		mop = _get_or_create_wallet_mop(company, cash_account)
		topup = _make_wallet_entry(company, "Wallet Payment", "Mode of Payment", "Cash", wallet, 100)

		si = create_sales_invoice(
			item=_ensure_pos_item(), qty=1, rate=100, is_pos=1, update_stock=0, do_not_save=True
		)
		si.set("payments", [])
		si.append("payments", {"mode_of_payment": mop, "amount": 100})
		si.insert()
		self.assertEqual(si.payments[0].account, wallet_account)
		si.submit()

		self._assert_gl_contains(
			"Sales Invoice",
			si.name,
			[
				{"account": wallet_account, "debit": 100, "credit": 0, "party": "_Test Customer"},
				{"account": "Sales - _TC", "debit": 0, "credit": 100, "party": None},
			],
		)
		cash_debit = sum(
			flt(r.debit)
			for r in frappe.get_all(
				"GL Entry",
				filters={"voucher_type": "Sales Invoice", "voucher_no": si.name, "is_cancelled": 0},
				fields=["account", "debit"],
			)
			if r.account == cash_account
		)
		self.assertEqual(cash_debit, 0)
		topup.reload()
		self.assertEqual(flt(topup.outstanding_amount), 0)
		self._assert_wallet_debit_against("Sales Invoice", si.name, wallet_account, topup.name)
		si.cancel()
		topup.reload()
		self.assertEqual(flt(topup.outstanding_amount), 100)

	def test_topup_si_then_transfer_outstanding(self):
		"""Wallet spend must reduce the same Wallet Entry outstanding that the top-up created.

		Top-up 1000 books a credit advance on that Wallet Entry. Paying an SI 400 with
		wallet must debit against that entry (outstanding 600), not open a new AR row.
		Transferring the remaining 600 must clear the source advance and leave a 600
		advance on the destination Wallet Entry.

		Cancel in reverse: transfer cancel restores 600 on the source top-up, then SI
		cancel restores the original 1000.
		"""
		company, cash_account, wallet_account = _company_accounts()
		source = _ensure_customer("_Test Wallet Source Customer")
		dest = _ensure_customer("_Test Wallet Dest Customer")
		wallet1 = _get_or_create_wallet(source, company, wallet_account)
		wallet2 = _get_or_create_wallet(dest, company, wallet_account)
		mop = _get_or_create_wallet_mop(company, cash_account)
		set_default_account_for_mode_of_payment(
			frappe.get_doc("Mode of Payment", "Cash"), company, cash_account
		)

		topup = _make_wallet_entry(company, "Wallet Payment", "Mode of Payment", "Cash", wallet1, 1000)
		self.assertEqual(flt(topup.outstanding_amount), 1000)

		si = create_sales_invoice(
			item=_ensure_pos_item(),
			qty=1,
			rate=400,
			is_pos=1,
			update_stock=0,
			customer=source,
			do_not_save=True,
		)
		si.set("payments", [])
		si.append("payments", {"mode_of_payment": mop, "amount": 400})
		si.insert()
		si.submit()

		topup.reload()
		self.assertEqual(flt(topup.outstanding_amount), 600)
		self._assert_wallet_debit_against("Sales Invoice", si.name, wallet_account, topup.name)
		self.assertRaises(frappe.ValidationError, topup.cancel)
		topup.reload()

		transfer = _make_wallet_entry(company, "Wallet Transfer", "Wallet", wallet1, wallet2, 600)
		topup.reload()
		transfer.reload()
		self.assertEqual(flt(topup.outstanding_amount), 0)
		self.assertEqual(flt(transfer.outstanding_amount), 600)
		self._assert_wallet_debit_against("Wallet Entry", transfer.name, wallet_account, topup.name)

		transfer.cancel()
		topup.reload()
		transfer.reload()
		self.assertEqual(flt(topup.outstanding_amount), 600)
		self.assertEqual(flt(transfer.outstanding_amount), 0)

		si.cancel()
		topup.reload()
		self.assertEqual(flt(topup.outstanding_amount), 1000)

	def test_cancel_wallet_payment_clears_outstanding(self):
		"""Cancelling a top-up zeros outstanding and reverses its GL."""
		company, cash_account, wallet_account = _company_accounts()
		customer = _ensure_customer("_Test Wallet Cancel Payment Customer")
		wallet = _get_or_create_wallet(customer, company, wallet_account)
		set_default_account_for_mode_of_payment(
			frappe.get_doc("Mode of Payment", "Cash"), company, cash_account
		)

		payment = _make_wallet_entry(company, "Wallet Payment", "Mode of Payment", "Cash", wallet, 500)
		self.assertEqual(flt(payment.outstanding_amount), 500)
		payment.cancel()
		payment.reload()
		self.assertEqual(flt(payment.outstanding_amount), 0)
		self.assertFalse(
			frappe.get_all(
				"GL Entry",
				filters={"voucher_type": "Wallet Entry", "voucher_no": payment.name, "is_cancelled": 0,},
				limit=1,
			)
		)

	def _assert_wallet_debit_against(self, voucher_type, voucher_no, account, wallet_entry):
		rows = frappe.get_all(
			"GL Entry",
			filters={
				"voucher_type": voucher_type,
				"voucher_no": voucher_no,
				"account": account,
				"debit": [">", 0],
				"is_cancelled": 0,
			},
			fields=["against_voucher_type", "against_voucher"],
			limit=1,
		)
		self.assertTrue(rows)
		self.assertEqual(rows[0].against_voucher_type, "Wallet Entry")
		self.assertEqual(rows[0].against_voucher, wallet_entry)

	def _assert_gl(self, voucher_type, voucher_no, expected):
		rows = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "is_cancelled": 0},
			fields=["account", "debit", "credit", "party"],
		)
		got = {(r.account, flt(r.debit), flt(r.credit), r.party or None) for r in rows}
		want = {(r["account"], flt(r["debit"]), flt(r["credit"]), r["party"]) for r in expected}
		self.assertEqual(got, want)

	def _assert_gl_contains(self, voucher_type, voucher_no, expected):
		rows = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "is_cancelled": 0},
			fields=["account", "debit", "credit", "party"],
		)
		got = {(r.account, flt(r.debit), flt(r.credit), r.party or None) for r in rows}
		for row in expected:
			self.assertIn((row["account"], flt(row["debit"]), flt(row["credit"]), row["party"]), got)


def _company_accounts():
	company = "_Test Company"
	return (
		company,
		"Cash - _TC",
		create_account(
			account_name="Customer Wallet",
			parent_account="Current Liabilities - _TC",
			company=company,
			account_type="Receivable",
		),
	)


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


def _ensure_customer(name):
	if frappe.db.exists("Customer", name):
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
			}
		)
		.insert()
		.name
	)


def _make_wallet_entry(company, transaction_type, transaction_from, source, to_wallet, amount):
	doc = frappe.get_doc(
		{
			"doctype": "Wallet Entry",
			"company": company,
			"posting_date": nowdate(),
			"transaction_type": transaction_type,
			"transaction_from": transaction_from,
			"source_of_payment": source,
			"to_wallet": to_wallet,
			"amount": amount,
		}
	).insert()
	doc.submit()
	return doc


def _ensure_pos_item():
	item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "Products"
	return make_item(
		"Wallet POS Test Item",
		properties={"is_stock_item": 0, "is_sales_item": 1, "item_group": item_group},
	).name


def _get_or_create_wallet_mop(company, fallback_account):
	name = "Wallet"
	if frappe.db.exists("Mode of Payment", name):
		mop = frappe.get_doc("Mode of Payment", name)
	else:
		mop = frappe.get_doc(
			{"doctype": "Mode of Payment", "mode_of_payment": name, "type": "General", "enabled": 1,}
		).insert()
	mop.is_wallet_payment = 1
	mop.save()
	set_default_account_for_mode_of_payment(mop, company, fallback_account)
	frappe.clear_document_cache("Mode of Payment", mop.name)
	return mop.name
