frappe.provide('erpnext.PointOfSale');
frappe.require('point-of-sale.bundle.js', function () {

    erpnext.PointOfSale.Payment = class CustomPayment extends erpnext.PointOfSale.Payment {
        constructor(wrapper, customer_wallet) {
            super(wrapper);
            this.customer_wallet = customer_wallet;
        }

        set_customer_wallet() {
            const doc = this.events.get_frm().doc;
            const customer = doc.customer;
            return new Promise((resolve) => {
                frappe.call({
                    method: "wallete.wallete.doctype.wallet.wallet.get_customer_wallet",
                    args: {customer: customer},
                    callback: (r) => {
                        if (!r.exc) {
                            this.customer_wallet = r.message;
                            resolve();
                        }
                    }
                });
            });
        }

        render_payment_mode_dom() {
            super.render_payment_mode_dom();
            const doc = this.events.get_frm().doc;
            const payments = doc.payments;
            const currency = doc.currency;
            const customer = doc.customer;
            this.set_customer_wallet()

            this.$payment_modes.html(`${
                payments.map((p, i) => {
                    const mode = p.mode_of_payment.replace(/ +/g, "_").toLowerCase();
                    const payment_type = p.type;
                    const margin = i % 2 === 0 ? 'pr-2' : 'pl-2';
                    const amount = p.amount > 0 ? format_currency(p.amount, currency) : '';

                    return (`
                        <div class="payment-mode-wrapper">
                            
                            <div class="mode-of-payment" data-mode="${mode}" data-payment-type="${payment_type}">
                                ${p.mode_of_payment} ${this.customer_wallet !== undefined ? ` ${customer} Wallet is ${this.customer_wallet} ` : ''}
                               
                                <div class="${mode}-amount pay-amount">${amount}</div>
                               
                                
                                <div class="${mode} mode-of-payment-control"></div>
                            </div>
                        </div>
                    `);
                }).join('')
            }`);

            payments.forEach(p => {
                const mode = p.mode_of_payment.replace(/ +/g, "_").toLowerCase();
                const me = this;
                this[`${mode}_control`] = frappe.ui.form.make_control({
                    df: {
                        label: p.mode_of_payment,
                        fieldtype: 'Currency',
                        placeholder: __('Enter {0} amount.', [p.mode_of_payment]),
                        onchange: function () {
                            const current_value = frappe.model.get_value(p.doctype, p.name, 'amount');
                            if (current_value != this.value) {
                                frappe.model
                                    .set_value(p.doctype, p.name, 'amount', flt(this.value))
                                    .then(() => me.update_totals_section())

                                const formatted_currency = format_currency(this.value, currency);
                                me.$payment_modes.find(`.${mode}-amount`).html(formatted_currency);
                            }
                        }
                    },
                    parent: this.$payment_modes.find(`.${mode}.mode-of-payment-control`),
                    render_input: true,
                });
                this[`${mode}_control`].toggle_label(false);
                this[`${mode}_control`].set_value(p.amount);
            });

            this.render_loyalty_points_payment_mode();

            this.attach_cash_shortcuts(doc);
        }

    };

    wrapper.pos = new erpnext.PointOfSale.Controller(wrapper);
    window.cur_pos = wrapper.pos;
});