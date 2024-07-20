// Copyright (c) 2024, Hamza Abuabada and contributors
// For license information, please see license.txt

frappe.ui.form.on('Wallet Entry', {
    setup: function (frm){
        set_to_wallet_field_query_filter(frm);
    },
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

	source_of_payment: function(frm) {
        set_to_wallet_field_query_filter(frm, frm.doc.transaction_type);
	},

    transaction_type: function (frm){
        if (frm.doc.transaction_type === "Wallet Payment"){
            frm.set_df_property('source_of_payment', 'label', "From Mode Of Payment");
            frm.doc.transaction_from = "Mode of Payment";
            frm.set_query("source_of_payment", ()=> {
                return {
                    filters: [ ['enabled', '=', 1] ]
                };
            });
        }else if (frm.doc.transaction_type === "Wallet Transfer"){
            frm.set_df_property('source_of_payment', 'label', "From Wallet");
            frm.doc.transaction_from = "Wallet";
            frm.set_query("source_of_payment", ()=> {
                return {
                    filters: [ ['status', '=', 'Active'] ]
                };
            });
        }
    }
});

function set_to_wallet_field_query_filter(frm, transaction_type=null){
    let filters = [ ['status', '=', 'Active'] ]
    if (transaction_type != null && transaction_type === "Wallet Transfer"){
        filters.push(['name', '!=', frm.doc.source_of_payment])
    }
    frm.set_query("to_wallet", ()=> {
        return {
            filters: filters
        };
    });
}
