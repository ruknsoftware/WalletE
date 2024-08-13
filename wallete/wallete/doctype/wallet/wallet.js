// Copyright (c) 2024, Hamza Abuabada and contributors
// For license information, please see license.txt

frappe.ui.form.on('Wallet', {
	setup: function(frm) {
		frm.set_query("account", ()=> {
			return {
				filters: [
					['account_type', '=', 'Receivable'],
					['is_group', '=', 0],
					['company', '=', frm.doc.company]
				]
			};
		});
	},
});
