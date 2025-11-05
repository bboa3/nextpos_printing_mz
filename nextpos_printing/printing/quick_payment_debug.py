#!/usr/bin/env python3
"""
Quick Payment Method Debugger for NextPOS Printing

This script helps you quickly debug payment method display issues
without needing to understand complex syntax.

Usage:
    bench --site YOUR-SITE console
    >>> from nextpos_printing.printing.quick_payment_debug import check_last_invoices
    >>> check_last_invoices()
"""

import frappe
from frappe import _


@frappe.whitelist()
def check_last_invoices(limit=5):
    """
    Check the last N POS invoices and show their payment methods.
    This helps identify if payment methods are being stored correctly.
    
    Args:
        limit: Number of recent invoices to check (default 5)
    
    Returns:
        dict: Invoice details with payment information
    """
    print("\n" + "="*80)
    print("CHECKING LAST POS INVOICES FOR PAYMENT METHODS")
    print("="*80 + "\n")
    
    # Get recent POS invoices from both POS Invoice and Sales Invoice (is_pos=1)
    # Try POS Invoice doctype first
    pos_invoices = frappe.db.sql("""
        SELECT 
            name,
            customer_name,
            posting_date,
            grand_total,
            pos_profile,
            'POS Invoice' as doctype_used
        FROM `tabPOS Invoice`
        WHERE docstatus = 1
        ORDER BY creation DESC
        LIMIT %s
    """, (limit,), as_dict=True)
    
    # Get Sales Invoices with is_pos=1 (POSAwesome, custom systems)
    sales_invoices = frappe.db.sql("""
        SELECT 
            name,
            customer_name,
            posting_date,
            grand_total,
            pos_profile,
            'Sales Invoice' as doctype_used
        FROM `tabSales Invoice`
        WHERE is_pos = 1 
          AND docstatus = 1
        ORDER BY creation DESC
        LIMIT %s
    """, (limit,), as_dict=True)
    
    # Combine and sort by date, take top N
    invoices = pos_invoices + sales_invoices
    invoices.sort(key=lambda x: x.posting_date, reverse=True)
    invoices = invoices[:limit]
    
    if not invoices:
        print("⚠️  No submitted POS invoices found.")
        print("     (Checked both POS Invoice and Sales Invoice with is_pos=1)")
        return {"error": "No invoices found"}
    
    results = []
    
    for idx, inv in enumerate(invoices, 1):
        print(f"\n{idx}. Invoice: {inv.name}")
        print(f"   DocType: {inv.doctype_used}")
        print(f"   Customer: {inv.customer_name}")
        print(f"   Date: {inv.posting_date}")
        print(f"   Total: {inv.grand_total}")
        print(f"   POS Profile: {inv.pos_profile or '(none)'}")
        
        # Get payment methods
        # Both POS Invoice and Sales Invoice use the same payment table: tabSales Invoice Payment
        payments = frappe.db.sql("""
            SELECT 
                mode_of_payment,
                amount,
                type,
                account,
                `default`
            FROM `tabSales Invoice Payment`
            WHERE parent = %s
            ORDER BY idx
        """, (inv.name,), as_dict=True)
        
        if payments:
            print(f"   Payment Methods ({len(payments)}):")
            for p_idx, payment in enumerate(payments, 1):
                print(f"      {p_idx}. {payment.mode_of_payment}")
                print(f"         Amount: {payment.amount}")
                print(f"         Type: {payment.type or 'N/A'}")
                print(f"         Default: {payment.get('default', 0)}")
                if payment.amount > 0:
                    print(f"         ✅ ACTIVE (will print on receipt)")
                else:
                    print(f"         ⚠️  Zero amount (won't print)")
        else:
            print(f"   ⚠️  NO PAYMENT METHODS FOUND!")
        
        results.append({
            "invoice": inv.name,
            "customer": inv.customer_name,
            "date": str(inv.posting_date),
            "total": inv.grand_total,
            "pos_profile": inv.pos_profile,
            "payments": payments
        })
    
    print("\n" + "="*80)
    print(f"Checked {len(invoices)} invoices")
    print("="*80 + "\n")
    
    return results


@frappe.whitelist()
def check_specific_invoice(invoice_name):
    """
    Check a specific invoice in detail.
    
    Args:
        invoice_name: Name of the POS Invoice to check
    
    Returns:
        dict: Detailed invoice and payment information
    """
    print("\n" + "="*80)
    print(f"CHECKING INVOICE: {invoice_name}")
    print("="*80 + "\n")
    
    # Check which doctype the invoice exists in
    invoice = None
    doctype_used = None
    
    if frappe.db.exists("POS Invoice", invoice_name):
        doctype_used = "POS Invoice"
        invoice = frappe.db.get_value(
            "POS Invoice",
            invoice_name,
            ["name", "customer", "customer_name", "posting_date", "posting_time", 
             "grand_total", "pos_profile", "is_pos", "docstatus"],
            as_dict=True
        )
    elif frappe.db.exists("Sales Invoice", invoice_name):
        doctype_used = "Sales Invoice"
        invoice = frappe.db.get_value(
            "Sales Invoice",
            invoice_name,
            ["name", "customer", "customer_name", "posting_date", "posting_time", 
             "grand_total", "pos_profile", "is_pos", "docstatus"],
            as_dict=True
        )
    else:
        print(f"❌ Invoice '{invoice_name}' not found!")
        print("   (Checked both POS Invoice and Sales Invoice)")
        return {"error": f"Invoice {invoice_name} not found"}
    
    print(f"Found in: {doctype_used}")
    print()
    
    print(f"Invoice Details:")
    print(f"  Customer: {invoice.customer_name} ({invoice.customer})")
    print(f"  Date: {invoice.posting_date} {invoice.posting_time or ''}")
    print(f"  Grand Total: {invoice.grand_total}")
    print(f"  POS Profile: {invoice.pos_profile or '(none)'}")
    print(f"  Is POS: {invoice.is_pos}")
    print(f"  Status: {['Draft', 'Submitted', 'Cancelled'][invoice.docstatus]}")
    print()
    
    # Get payments
    # Both POS Invoice and Sales Invoice use the same payment table
    payments = frappe.db.sql("""
        SELECT 
            idx,
            mode_of_payment,
            amount,
            base_amount,
            type,
            account,
            `default`,
            reference_no
        FROM `tabSales Invoice Payment`
        WHERE parent = %s
        ORDER BY idx
    """, (invoice_name,), as_dict=True)
    
    if not payments:
        print("❌ NO PAYMENT METHODS FOUND!")
        print("   This is unusual for a POS invoice.\n")
        return {
            "invoice": invoice,
            "payments": [],
            "error": "No payments found"
        }
    
    print(f"Payment Methods ({len(payments)}):")
    print("-" * 80)
    
    for payment in payments:
        print(f"\n  Payment #{payment.idx}:")
        print(f"    Mode: {payment.mode_of_payment}")
        print(f"    Amount: {payment.amount}")
        print(f"    Base Amount: {payment.base_amount or 'N/A'}")
        print(f"    Type: {payment.type or 'N/A'}")
        print(f"    Account: {payment.account or 'N/A'}")
        print(f"    Default: {'Yes' if payment.get('default') else 'No'}")
        print(f"    Reference: {payment.reference_no or 'N/A'}")
        
        # Check if this will print
        if payment.amount != 0:
            print(f"    ✅ WILL PRINT ON RECEIPT (amount > 0)")
        else:
            print(f"    ⚠️  WON'T PRINT (amount = 0)")
    
    print("\n" + "="*80)
    
    # Check POS Profile if available
    if invoice.pos_profile:
        print(f"\nChecking POS Profile: {invoice.pos_profile}")
        print("-" * 80)
        
        profile_payments = frappe.db.sql("""
            SELECT 
                idx,
                mode_of_payment,
                `default`,
                allow_in_returns
            FROM `tabSales Invoice Payment` 
            WHERE parent = %s
            ORDER BY idx
        """, (invoice.pos_profile,), as_dict=True)
        
        if profile_payments:
            print(f"POS Profile has {len(profile_payments)} payment methods:")
            for p in profile_payments:
                default_marker = " ⭐ DEFAULT" if p.get('default') else ""
                first_marker = " (FIRST - used if nothing selected)" if p.idx == 1 else ""
                print(f"  {p.idx}. {p.mode_of_payment}{default_marker}{first_marker}")
        else:
            print("⚠️  POS Profile has no payment methods configured!")
    
    print("\n" + "="*80)
    print("ANALYSIS:")
    print("="*80)
    
    # Analyze the issue
    active_payments = [p for p in payments if p.amount != 0]
    
    if len(active_payments) == 0:
        print("❌ No active payments found!")
    elif len(active_payments) == 1:
        print(f"✅ One payment method will print: {active_payments[0].mode_of_payment}")
    else:
        print(f"⚠️  Multiple payment methods ({len(active_payments)}):")
        for p in active_payments:
            print(f"   - {p.mode_of_payment}: {p.amount}")
        print(f"\n   Receipt will show: {active_payments[0].mode_of_payment}")
        print(f"   (Only first payment is displayed on receipt)")
    
    print("\n")
    
    return {
        "invoice": invoice,
        "payments": payments,
        "active_payments": active_payments
    }


@frappe.whitelist()
def check_pos_profile(pos_profile_name):
    """
    Check POS Profile payment configuration.
    
    Args:
        pos_profile_name: Name of the POS Profile
    
    Returns:
        dict: POS Profile payment configuration
    """
    print("\n" + "="*80)
    print(f"CHECKING POS PROFILE: {pos_profile_name}")
    print("="*80 + "\n")
    
    if not frappe.db.exists("POS Profile", pos_profile_name):
        print(f"❌ POS Profile '{pos_profile_name}' not found!")
        return {"error": f"POS Profile {pos_profile_name} not found"}
    
    # Get profile details
    profile = frappe.db.get_value(
        "POS Profile",
        pos_profile_name,
        ["name", "company", "currency", "disabled"],
        as_dict=True
    )
    
    print(f"Profile Details:")
    print(f"  Company: {profile.company}")
    print(f"  Currency: {profile.currency}")
    print(f"  Status: {'Disabled' if profile.disabled else 'Active'}")
    print()
    
    # Get payment methods - using correct parent table
    payments = frappe.db.sql("""
        SELECT 
            idx,
            mode_of_payment,
            `default`,
            allow_in_returns
        FROM `tabPOS Payment Method`
        WHERE parent = %s
        ORDER BY idx
    """, (pos_profile_name,), as_dict=True)
    
    if not payments:
        print("❌ NO PAYMENT METHODS CONFIGURED!")
        print("   This POS Profile has no payment methods.\n")
        return {
            "profile": profile,
            "payments": [],
            "error": "No payment methods configured"
        }
    
    print(f"Payment Methods ({len(payments)}):")
    print("-" * 80)
    
    default_payment = None
    first_payment = None
    
    for payment in payments:
        markers = []
        
        if payment.idx == 1:
            markers.append("FIRST")
            first_payment = payment.mode_of_payment
        
        if payment.get('default'):
            markers.append("⭐ DEFAULT")
            default_payment = payment.mode_of_payment
        
        marker_str = f" [{', '.join(markers)}]" if markers else ""
        
        print(f"  {payment.idx}. {payment.mode_of_payment}{marker_str}")
        print(f"     Allow in returns: {'Yes' if payment.allow_in_returns else 'No'}")
    
    print("\n" + "="*80)
    print("IMPORTANT:")
    print("="*80)
    print(f"\n1. First payment method: {first_payment}")
    print(f"   This will be used if no payment is selected in POS.")
    
    if default_payment:
        print(f"\n2. Default payment method: {default_payment}")
        print(f"   This should be pre-selected in POS interface.")
    else:
        print(f"\n2. No default payment set.")
        print(f"   Consider marking one as default for faster checkout.")
    
    print(f"\n⚠️  If all invoices show '{first_payment}', this means:")
    print(f"   - Payment selection is not being saved correctly")
    print(f"   - OR cashiers are not selecting payment method")
    print(f"   - OR POSAwesome is always using first payment\n")
    
    return {
        "profile": profile,
        "payments": payments,
        "first_payment": first_payment,
        "default_payment": default_payment
    }


# Convenience function to print usage
def help():
    """Print help information"""
    print("\n" + "="*80)
    print("NEXTPOS PAYMENT DEBUG - USAGE GUIDE")
    print("="*80 + "\n")
    
    print("In bench console:")
    print("-" * 80)
    print("from nextpos_printing.printing.quick_payment_debug import *")
    print()
    print("# Check last 5 invoices")
    print("check_last_invoices()")
    print()
    print("# Check specific invoice")
    print("check_specific_invoice('POS-INV-2024-00001')")
    print()
    print("# Check POS Profile")
    print("check_pos_profile('Main POS Profile')")
    print()
    print("\nIn browser console:")
    print("-" * 80)
    print("frappe.call({")
    print("    method: 'nextpos_printing.printing.quick_payment_debug.check_last_invoices',")
    print("    callback: (r) => console.log(r.message)")
    print("});")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    help()

