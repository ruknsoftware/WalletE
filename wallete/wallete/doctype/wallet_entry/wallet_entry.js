// Copyright (c) 2024, Hamza Abuabada and contributors
// For license information, please see license.txt

frappe.ui.form.on('Wallet Entry', {
    refresh: function (frm){
        if(frm.doc.docstatus > 0) {
			frm.add_custom_button(__('Ledger'), function() {
				frappe.route_options = {
					"voucher_no": frm.doc.name,
					"from_date": frm.doc.posting_date,
					"to_date": moment(frm.doc.modified).format('YYYY-MM-DD'),
					"company": frm.doc.company,
					"group_by": '',
					"show_cancelled_entries": frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "General Ledger");
			});
		}
    },
	mode_of_payment: function(frm) {
        if (frm.doc.transaction_type === "Wallet Transfer"){
            frm.set_query("wallet", ()=> {
                return {
                    filters: [
                        ['name', '!=', frm.doc.mode_of_payment],
                    ]
                };
            });
        }

	},
    transaction_type: function (frm){
        if (frm.doc.transaction_type === "Wallet Payment"){
            frm.doc.transaction_from = "Mode of Payment";
        }else if (frm.doc.transaction_type === "Wallet Transfer"){
            frm.doc.transaction_from = "Wallet";
        }
    }
});
