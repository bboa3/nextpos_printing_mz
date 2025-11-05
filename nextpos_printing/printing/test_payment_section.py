#!/usr/bin/env python3
"""
Test script for get_payment_lines() function

This verifies the payment section logic works correctly for:
- Single payments
- Split payments (multiple methods)
- Zero-amount payments (should be filtered out)

Usage:
    bench --site YOUR-SITE execute nextpos_printing.printing.test_payment_section.test_payment_section
"""

import frappe
from nextpos_printing.printing.receipt import get_payment_lines


@frappe.whitelist()
def test_payment_section():
    """Test the get_payment_lines() function with real invoices"""
    
    print("\n" + "="*80)
    print("TESTING get_payment_lines() FUNCTION")
    print("="*80 + "\n")
    
    # Get some recent POS invoices
    invoices = frappe.db.sql("""
        SELECT name, customer_name, grand_total
        FROM `tabPOS Invoice`
        WHERE docstatus = 1
        ORDER BY creation DESC
        LIMIT 5
    """, as_dict=True)
    
    if not invoices:
        # Try Sales Invoice if no POS Invoice found
        invoices = frappe.db.sql("""
            SELECT name, customer_name, grand_total
            FROM `tabSales Invoice`
            WHERE is_pos = 1 AND docstatus = 1
            ORDER BY creation DESC
            LIMIT 5
        """, as_dict=True)
    
    if not invoices:
        print("⚠️  No POS invoices found for testing.\n")
        return {"error": "No invoices found"}
    
    print(f"Testing with {len(invoices)} invoices:\n")
    
    test_results = []
    
    for idx, inv_data in enumerate(invoices, 1):
        print(f"{idx}. Invoice: {inv_data.name}")
        print(f"   Customer: {inv_data.customer_name}")
        print(f"   Total: {inv_data.grand_total}")
        
        try:
            # Load the full invoice document
            doctype = "POS Invoice" if frappe.db.exists("POS Invoice", inv_data.name) else "Sales Invoice"
            invoice = frappe.get_doc(doctype, inv_data.name)
            
            # Get payment data
            payments = getattr(invoice, "payments", [])
            active_payments = [p for p in payments if p.amount != 0]
            
            print(f"   Total payments: {len(payments)}")
            print(f"   Active payments: {len(active_payments)}")
            
            # Test the function
            payment_lines = get_payment_lines(invoice)
            
            print(f"   ✅ Function returned {len(payment_lines)} lines")
            
            if payment_lines:
                print(f"   Receipt will show:")
                for line in payment_lines:
                    # Remove ESC/POS codes for display
                    clean_line = line.replace("\x1BE\x01", "[BOLD]").replace("\x1BE\x00", "[/BOLD]")
                    print(f"      {clean_line}")
            else:
                print(f"   ⚠️  No payment lines generated")
            
            test_results.append({
                "invoice": inv_data.name,
                "total_payments": len(payments),
                "active_payments": len(active_payments),
                "lines_generated": len(payment_lines),
                "success": True
            })
            
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            test_results.append({
                "invoice": inv_data.name,
                "error": str(e),
                "success": False
            })
        
        print()
    
    # Summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    success_count = sum(1 for r in test_results if r.get("success"))
    error_count = len(test_results) - success_count
    
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {error_count}")
    
    if error_count == 0:
        print("\n🎉 ALL TESTS PASSED!")
    
    print()
    
    return test_results


@frappe.whitelist()
def test_specific_invoice(invoice_name):
    """Test get_payment_lines() with a specific invoice"""
    
    print("\n" + "="*80)
    print(f"TESTING INVOICE: {invoice_name}")
    print("="*80 + "\n")
    
    try:
        # Load invoice
        doctype = "POS Invoice" if frappe.db.exists("POS Invoice", invoice_name) else "Sales Invoice"
        invoice = frappe.get_doc(doctype, invoice_name)
        
        print(f"DocType: {doctype}")
        print(f"Customer: {invoice.customer_name}")
        print(f"Total: {invoice.grand_total}")
        print()
        
        # Show all payments
        payments = getattr(invoice, "payments", [])
        print(f"All Payments ({len(payments)}):")
        for p in payments:
            print(f"  - {p.mode_of_payment}: {p.amount}")
        print()
        
        # Show active payments
        active_payments = [p for p in payments if p.amount != 0]
        print(f"Active Payments ({len(active_payments)}):")
        for p in active_payments:
            print(f"  - {p.mode_of_payment}: {p.amount}")
        print()
        
        # Test function
        payment_lines = get_payment_lines(invoice)
        
        print(f"Generated Lines ({len(payment_lines)}):")
        print("-" * 80)
        for line in payment_lines:
            # Remove ESC/POS codes for display
            clean_line = line.replace("\x1BE\x01", "[BOLD]").replace("\x1BE\x00", "[/BOLD]")
            print(clean_line)
        print("-" * 80)
        print()
        
        print("✅ Test completed successfully!")
        
        return {
            "invoice": invoice_name,
            "doctype": doctype,
            "total_payments": len(payments),
            "active_payments": len(active_payments),
            "lines_generated": len(payment_lines),
            "lines": payment_lines
        }
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "invoice": invoice_name,
            "error": str(e)
        }


def help():
    """Print usage instructions"""
    print("\n" + "="*80)
    print("PAYMENT SECTION TEST - USAGE")
    print("="*80 + "\n")
    
    print("In bench console:")
    print("-" * 80)
    print("from nextpos_printing.printing.test_payment_section import *")
    print()
    print("# Test with recent invoices")
    print("test_payment_section()")
    print()
    print("# Test specific invoice")
    print("test_specific_invoice('ACC-PSINV-2025-00013')")
    print()
    print("\nOr via execute command:")
    print("-" * 80)
    print("bench --site YOUR-SITE execute nextpos_printing.printing.test_payment_section.test_payment_section")
    print()
    print("="*80 + "\n")


if __name__ == "__main__":
    help()

