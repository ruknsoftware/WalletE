frappe.provide('erpnext.PointOfSale');
frappe.require('point-of-sale.bundle.js', function () {

    erpnext.PointOfSale.Payment = class CustomPayment extends erpnext.PointOfSale.Payment {
        constructor({ events, wrapper }) {
            super({ events, wrapper });
            this.bind_event_show_customer_wallet()
        }

        set_customer_wallet() {
            // THIS IS OUR FUNCTION
            const pos_invoice = this.events.get_frm().doc;
            const customer = pos_invoice.customer;
            return new Promise((resolve) => {
                frappe.call({
                    method: "wallete.wallete.doctype.wallet.wallet.get_customer_wallet",
                    args: {customer: customer, exclude_invoice: pos_invoice.name},
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
            const pos_invoice = this.events.get_frm().doc;
            const payments = pos_invoice.payments;
            payments.forEach(payment => {
                frappe.db.get_value('Mode of Payment', payment.mode_of_payment, ["is_wallet_payment"], function (value) {
                    payment.is_wallet_payment = value.is_wallet_payment;
                });
            })
        }

        render_payment_mode_dom() {
            super.render_payment_mode_dom();
            // THIS IS OUR CODE
            this.set_customer_wallet();
            this.set_payment_modes_is_wallet();
            const pos_invoice = this.events.get_frm().doc;
            const customer = pos_invoice.customer;
            const currency = pos_invoice.currency;
            const payments = pos_invoice.payments;
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