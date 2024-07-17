// Copyright (c) 2024, Hamza Abuabada and contributors
// For license information, please see license.txt

frappe.ui.form.on('Wallet Entry', {
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
