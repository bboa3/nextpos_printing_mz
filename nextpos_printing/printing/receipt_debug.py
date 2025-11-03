"""
Diagnostic utilities for debugging NextPOS Printing issues
"""
import frappe
import json

@frappe.whitelist()
def debug_invoice_payment(invoice_name):
    """
    Debug utility to see what payment data is stored in the invoice.
    
    Usage in browser console:
    frappe.call({
        method: 'nextpos_printing.printing.receipt_debug.debug_invoice_payment',
        args: { invoice_name: 'POS-INV-2024-00001' },
        callback: (r) => console.log(r.message)
    });
    """
    try:
        invoice = frappe.get_doc("POS Invoice", invoice_name)
    except frappe.DoesNotExistError:
        # Try Sales Invoice (POSAwesome might use Sales Invoice instead)
        try:
            invoice = frappe.get_doc("Sales Invoice", invoice_name)
        except:
            return {
                "error": True,
                "message": f"Invoice {invoice_name} not found in POS Invoice or Sales Invoice"
            }
    
    payment_details = []
    for idx, payment in enumerate(invoice.payments):
        payment_details.append({
            "index": idx,
            "mode_of_payment": payment.mode_of_payment,
            "amount": payment.amount,
            "base_amount": getattr(payment, 'base_amount', None),
            "default": getattr(payment, 'default', None),
            "type": getattr(payment, 'type', None),
            "account": getattr(payment, 'account', None),
            "reference_no": getattr(payment, 'reference_no', None),
        })
    
    return {
        "invoice": invoice_name,
        "doctype": invoice.doctype,
        "customer": invoice.customer_name or invoice.customer,
        "posting_date": str(invoice.posting_date),
        "posting_time": str(getattr(invoice, 'posting_time', '')),
        "grand_total": invoice.grand_total,
        "paid_amount": getattr(invoice, 'paid_amount', 0),
        "change_amount": getattr(invoice, 'change_amount', 0),
        "pos_profile": getattr(invoice, 'pos_profile', ''),
        "payments_count": len(invoice.payments),
        "payments": payment_details
    }


@frappe.whitelist()
def debug_pos_profile(pos_profile_name):
    """
    Debug utility to see payment methods configured in a POS Profile.
    
    Usage in browser console:
    frappe.call({
        method: 'nextpos_printing.printing.receipt_debug.debug_pos_profile',
        args: { pos_profile_name: 'Main POS' },
        callback: (r) => console.log(r.message)
    });
    """
    try:
        profile = frappe.get_doc("POS Profile", pos_profile_name)
    except:
        return {
            "error": True,
            "message": f"POS Profile {pos_profile_name} not found"
        }
    
    payment_methods = []
    for idx, payment in enumerate(profile.payments):
        payment_methods.append({
            "index": idx,
            "mode_of_payment": payment.mode_of_payment,
            "default": payment.default,
            "allow_in_returns": getattr(payment, 'allow_in_returns', None),
        })
    
    return {
        "pos_profile": pos_profile_name,
        "company": profile.company,
        "currency": profile.currency,
        "payment_methods_count": len(profile.payments),
        "payment_methods": payment_methods
    }


@frappe.whitelist()
def compare_invoice_to_profile(invoice_name):
    """
    Compare invoice payment methods against POS Profile configuration.
    
    Usage in browser console:
    frappe.call({
        method: 'nextpos_printing.printing.receipt_debug.compare_invoice_to_profile',
        args: { invoice_name: 'POS-INV-2024-00001' },
        callback: (r) => console.log(r.message)
    });
    """
    invoice_data = debug_invoice_payment(invoice_name)
    
    if invoice_data.get('error'):
        return invoice_data
    
    if not invoice_data.get('pos_profile'):
        return {
            "error": True,
            "message": "Invoice has no POS Profile linked"
        }
    
    profile_data = debug_pos_profile(invoice_data['pos_profile'])
    
    if profile_data.get('error'):
        return profile_data
    
    # Compare payment methods
    invoice_payment_modes = [p['mode_of_payment'] for p in invoice_data['payments'] if p['amount'] > 0]
    profile_payment_modes = [p['mode_of_payment'] for p in profile_data['payment_methods']]
    
    analysis = {
        "invoice": invoice_name,
        "pos_profile": invoice_data['pos_profile'],
        "invoice_payment_methods": invoice_payment_modes,
        "profile_payment_methods": profile_payment_modes,
        "profile_default_payment": next(
            (p['mode_of_payment'] for p in profile_data['payment_methods'] if p['default']),
            profile_payment_modes[0] if profile_payment_modes else None
        ),
        "invoice_uses_default": False,
        "issues": []
    }
    
    # Check if invoice is using the default/first payment method
    if invoice_payment_modes:
        first_invoice_payment = invoice_payment_modes[0]
        if first_invoice_payment == profile_payment_modes[0]:
            analysis['invoice_uses_default'] = True
            analysis['issues'].append(
                "Invoice is using the first payment method from POS Profile. "
                "This may indicate the selected payment method is not being saved correctly."
            )
    
    # Check for multiple payments
    if len(invoice_payment_modes) > 1:
        analysis['issues'].append(
            f"Invoice has {len(invoice_payment_modes)} payment methods. "
            "Receipt will only show the first one."
        )
    
    return analysis

