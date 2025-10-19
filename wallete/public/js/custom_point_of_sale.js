frappe.provide('erpnext.PointOfSale');
frappe.require('point-of-sale.bundle.js', function () {

    const BasePayment = erpnext.PointOfSale.Payment;
    erpnext.PointOfSale.Payment = class CustomPayment extends BasePayment {
        constructor(options) {
            super(options);
            
        }

        set_customer_wallet() {
            // THIS IS OUR FUNCTION
            const pos_invoice = this.events.get_frm().doc;
            const customer = pos_invoice.customer;
            if (!customer) {
                this.customer_wallet = 0;
                return Promise.resolve();
            }
            return new Promise((resolve) => {
                frappe.call({
                    method: "wallete.wallete.doctype.wallet.wallet.get_customer_wallet_balance",
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
            const payments = (pos_invoice.payments || []);
            payments.forEach(payment => {
                if (!payment || !payment.mode_of_payment) return;
                frappe.db.get_value('Mode of Payment', payment.mode_of_payment, ["is_wallet_payment"], function (value) {
                    payment.is_wallet_payment = value && (value.is_wallet_payment || 0);
                });
            });
        }

        render_payment_mode_dom() {
            super.render_payment_mode_dom();
            // THIS IS OUR CODE
            this.bind_event_show_customer_wallet();
            this.set_payment_modes_is_wallet();
            const pos_invoice = this.events.get_frm().doc;
            const customer = pos_invoice.customer;
            const currency = pos_invoice.currency;
            const payments = (pos_invoice.payments || []);
            this.set_customer_wallet()
                .then(() => {
                    const customer_wallet = this.customer_wallet > 0 ? format_currency(this.customer_wallet, currency) : '';

                    payments.forEach(payment => {
                        this.attach_customer_wallet(payment, customer, customer_wallet);
                    });
                })
                .catch(() => {
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
                this.customer_wallet !== undefined && this.customer_wallet > 0.0 && !!payment.is_wallet_payment
            ) {
                this.$payment_modes.find('.customer-wallet').remove();
                this.$payment_modes.find(`[data-payment-type="${payment.type}"]`).find('.mode-of-payment-control')
                    .after((`<div class="customer-wallet">${customer} Wallet have ${customer_wallet}</div>`));
                $(`.customer-wallet`).css('display', 'none');
            }
        }
    };



});