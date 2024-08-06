frappe.provide('erpnext.PointOfSale');
frappe.require('point-of-sale.bundle.js', function () {

    erpnext.PointOfSale.Payment = class CustomPayment extends erpnext.PointOfSale.Payment {
        constructor({ events, wrapper }) {
            super({ events, wrapper });
            this.bind_event_show_customer_wallet()
        }

        set_customer_wallet() {
            // THIS IS OUR FUNCTION
            const pos_profile = this.events.get_frm().doc;
            const customer = pos_profile.customer;
            return new Promise((resolve) => {
                frappe.call({
                    method: "wallete.wallete.doctype.wallet.wallet.get_customer_wallet",
                    args: {customer: customer},
                    callback: (customer_wallet) => {
                        if (!customer_wallet.exc) {
                            this.customer_wallet = customer_wallet.message;
                            resolve();
                        }
                    }
                });
            });
        }

        set_payment_modes_is_wallet() {
            // THIS IS OUR FUNCTION
            const pos_profile = this.events.get_frm().doc;
            const payments = pos_profile.payments;
            payments.forEach(payment => {
                frappe.db.get_value('Mode of Payment', payment.mode_of_payment, ["is_wallet_payment"], function (value) {
                    payment.is_wallet_payment = value.is_wallet_payment;
                });
            })
        }

        render_payment_mode_dom() {
            super.render_payment_mode_dom();
            // ERPNEXT CODE
            const pos_profile = this.events.get_frm().doc;
            const payments = pos_profile.payments;
            const currency = pos_profile.currency;
            const customer = pos_profile.customer;

            this.$payment_modes.html(`${
                payments.map((payment, index) => {
                    const mode = payment.mode_of_payment.replace(/ +/g, "_").toLowerCase();
                    const payment_type = payment.type;
                    const margin = index % 2 === 0 ? 'pr-2' : 'pl-2';
                    const amount = payment.amount > 0 ? format_currency(payment.amount, currency) : '';

                    return (`
                        <div class="payment-mode-wrapper">
                            <div class="mode-of-payment" data-mode="${mode}" data-payment-type="${payment_type}">
                                ${payment.mode_of_payment}
                                <div class="${mode}-amount pay-amount">${amount}</div>
                                <div class="${mode} mode-of-payment-control"></div>
                            </div>
                        </div>
                    `);
                }).join('')
            }`);

            payments.forEach(payment => {
                const mode = payment.mode_of_payment.replace(/ +/g, "_").toLowerCase();
                const me = this;
                this[`${mode}_control`] = frappe.ui.form.make_control({
                    df: {
                        label: payment.mode_of_payment,
                        fieldtype: 'Currency',
                        placeholder: __('Enter {0} amount.', [payment.mode_of_payment]),
                        onchange: function () {
                            const current_value = frappe.model.get_value(payment.doctype, payment.name, 'amount');
                            if (current_value != this.value) {
                                frappe.model
                                    .set_value(payment.doctype, payment.name, 'amount', flt(this.value))
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
                this[`${mode}_control`].set_value(payment.amount);
            });

            this.render_loyalty_points_payment_mode();

            this.attach_cash_shortcuts(pos_profile);

            // THIS IS OUR CODE
            this.set_customer_wallet();
            this.set_payment_modes_is_wallet();
            const customer_wallet = this.customer_wallet > 0 ? format_currency(this.customer_wallet, currency) : '';

            payments.forEach(payment => {
                this.attach_customer_wallet(payment, customer, customer_wallet);

            });

        }

        bind_event_show_customer_wallet() {
            // THIS IS OUR FUNCTION
            this.$payment_modes.on('click', '.mode-of-payment', function (e) {
                const mode_clicked = $(this);
                $(`.customer-wallet`).css('display', 'none');
                if (mode_clicked.hasClass('border-primary')) {
                    mode_clicked.find('.customer-wallet').css('display', 'grid');
                }
            });
        }

        attach_customer_wallet(payment, customer, customer_wallet) {
            // THIS IS OUR FUNCTION
            if (
                this.customer_wallet !== undefined && this.customer_wallet > 0.0 && payment.is_wallet_payment === 1
            ) {
                this.$payment_modes.find('.customer-wallet').remove();
                this.$payment_modes.find(`[data-payment-type="${payment.type}"]`).find('.mode-of-payment-control')
                    .after((`<div class="customer-wallet">${customer} Wallet have ${customer_wallet}</div>`));
                $(`.customer-wallet`).css('display', 'none');
            }
        }
    };

    wrapper.pos = new erpnext.PointOfSale.Controller(wrapper);
    window.cur_pos = wrapper.pos;
});