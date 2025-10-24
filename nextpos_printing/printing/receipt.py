import frappe
import re
import datetime

DEFAULT_WIDTH = 48  # characters per line for 80mm thermal (adjusted from 42)


def wrap_text(text: str, width: int = DEFAULT_WIDTH):
    """Wrap text to fit thermal printer width."""
    lines = []
    while len(text) > width:
        lines.append(text[:width])
        text = text[width:]
    if text:
        lines.append(text)
    return lines


def format_custom_block(text: str, width: int):
    """Clean and center-align each line of custom header/footer text."""
    if not text:
        return []

    # Replace HTML breaks and paragraphs with newlines
    clean = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    clean = re.sub(r"</?p.*?>", "\n", clean, flags=re.I)

    # Strip remaining HTML tags
    clean = frappe.utils.strip_html_tags(clean or "")

    # Split and center
    formatted = []
    for ln in [ln.strip() for ln in clean.split("\n") if ln.strip()]:
        for wrapped in wrap_text(ln, width):
            formatted.append(wrapped.center(width))
    return formatted


def format_amount(amount, include_currency=False):
    """Format amount with proper decimal places and optional currency."""
    formatted = f"{amount:,.2f}"
    if include_currency:
        formatted += " MZN"
    return formatted


def dashed_line(width):
    """Create a dashed separator line."""
    return "-" * width


def solid_line(width):
    """Create a solid separator line."""
    return "=" * width


def format_table_row(col1, col2, col3, width, col1_width, col2_width):
    """
    Format a 3-column table row for items.
    col1: Description (left-aligned)
    col2: Quantity (right-aligned)
    col3: Value (right-aligned)
    """
    col3_width = width - col1_width - col2_width - 2  # 2 spaces for padding
    
    # Truncate or pad columns
    col1_text = col1[:col1_width].ljust(col1_width)
    col2_text = str(col2).rjust(col2_width)
    col3_text = str(col3).rjust(col3_width)
    
    return f"{col1_text} {col2_text} {col3_text}"


def get_company_info(company_name):
    """Retrieve company information."""
    try:
        company = frappe.get_doc("Company", company_name)
        return {
            "name": company.company_name or company_name,
            "address": get_company_address(company),
            "tax_id": company.tax_id or "",
            "phone": company.phone_no or "",
            "email": company.email or ""
        }
    except:
        return {
            "name": company_name,
            "address": "",
            "tax_id": "",
            "phone": "",
            "email": ""
        }


def get_company_address(company):
    """Get formatted company address."""
    try:
        # Try to get default company address
        address_links = frappe.get_all(
            "Dynamic Link",
            filters={
                "link_doctype": "Company",
                "link_name": company.name,
                "parenttype": "Address"
            },
            fields=["parent"]
        )
        
        if address_links:
            address = frappe.get_doc("Address", address_links[0].parent)
            parts = []
            if address.address_line1:
                parts.append(address.address_line1)
            if address.city:
                parts.append(address.city)
            return ", ".join(parts) if parts else ""
    except:
        pass
    return ""


def get_customer_tax_id(customer_name):
    """Retrieve customer tax ID (NUIT)."""
    try:
        customer = frappe.get_doc("Customer", customer_name)
        return customer.tax_id or ""
    except:
        return ""


def render_invoice(invoice_name: str):
    """Render a POS Invoice into ESC/POS raw lines for thermal printers (80mm format)."""
    invoice = frappe.get_doc("POS Invoice", invoice_name)
    settings = frappe.get_single("NextPOS Settings")
    width = int(settings.paper_width or DEFAULT_WIDTH)

    lines = []

    # ========== HEADER SECTION ==========
    company_info = get_company_info(invoice.company)
    
    # Company name (bold)
    lines.append("\x1BE\x01" + company_info["name"].center(width) + "\x1BE\x00")
    
    # Company address
    if company_info["address"]:
        lines.append(company_info["address"].center(width))
    
    # Company tax ID (NUIT)
    if company_info["tax_id"]:
        lines.append(f"NUIT: {company_info['tax_id']}".center(width))
    
    lines.append("")
    lines.append(dashed_line(width))
    lines.append("")

    # ========== CUSTOMER INFO SECTION ==========
    customer_display = invoice.customer_name or invoice.customer
    lines.append("\x1BE\x01Cliente:\x1BE\x00 " + customer_display)
    
    # Customer NUIT
    customer_tax_id = get_customer_tax_id(invoice.customer)
    if customer_tax_id:
        lines.append("\x1BE\x01NUIT:\x1BE\x00 " + customer_tax_id)
    
    # Date and time (combine posting_date and posting_time)
    posting_datetime = datetime.datetime.combine(
        invoice.posting_date,
        invoice.posting_time or datetime.time(0, 0)
    )
    date_str = frappe.utils.format_datetime(posting_datetime, "dd/MM/yyyy HH:mm")
    lines.append("\x1BE\x01Data:\x1BE\x00 " + date_str)
    
    # Invoice number
    lines.append("\x1BE\x01Fatura No:\x1BE\x00 " + invoice.name)
    
    lines.append("")
    lines.append(dashed_line(width))
    lines.append("")

    # ========== ITEMS TABLE ==========
    # Table column widths (adjust based on paper width)
    col1_width = int(width * 0.60)  # Description: 60%
    col2_width = int(width * 0.10)  # Quantity: 10%
    col3_width = width - col1_width - col2_width - 2  # Value: remaining
    
    # Table header
    header_row = format_table_row("Descricao", "Qtd", "Valor", width, col1_width, col2_width)
    lines.append("\x1BE\x01" + header_row + "\x1BE\x00")
    
    # Table rows
    for item in invoice.items:
        item_name = item.item_name[:col1_width]  # Truncate if too long
        qty_str = f"{item.qty:.0f}"
        amount_str = format_amount(item.amount)
        
        item_row = format_table_row(item_name, qty_str, amount_str, width, col1_width, col2_width)
        lines.append(item_row)
    
    lines.append("")
    lines.append(dashed_line(width))
    lines.append("")

    # ========== TOTALS SECTION ==========
    # Sub-total (net total before taxes)
    subtotal = invoice.net_total or invoice.total
    subtotal_str = format_amount(subtotal, include_currency=True)
    lines.append("Sub-total".ljust(width - len(subtotal_str)) + subtotal_str)
    
    # Taxes
    if getattr(invoice, "taxes", []):
        for tax in invoice.taxes:
            tax_label = tax.description[:20]  # Truncate tax name
            tax_amount_str = format_amount(tax.tax_amount, include_currency=True)
            lines.append(tax_label.ljust(width - len(tax_amount_str)) + tax_amount_str)
    
    # Grand total (bold)
    total_str = format_amount(invoice.grand_total, include_currency=True)
    lines.append("\x1BE\x01" + "TOTAL".ljust(width - len(total_str)) + total_str + "\x1BE\x00")
    
    lines.append("")
    lines.append(dashed_line(width))
    lines.append("")

    # ========== PAYMENT SECTION ==========
    if getattr(invoice, "payments", []):
        for payment in invoice.payments:
            mode = payment.mode_of_payment or "Dinheiro"
            lines.append("\x1BE\x01Pagamento:\x1BE\x00 " + mode)
            
            # Payment reference (if available)
            if hasattr(payment, "reference_no") and payment.reference_no:
                lines.append("\x1BE\x01Ref.:\x1BE\x00 " + payment.reference_no)
            break  # Show only first payment method
    
    # Change due
    change = getattr(invoice, "change_amount", 0.00)
    if change > 0:
        change_str = format_amount(change, include_currency=True)
        lines.append("Troco: " + change_str)
    
    lines.append("")
    lines.append(dashed_line(width))
    lines.append("")

    # ========== FOOTER SECTION ==========
    # "TOTAL A PAGAR" centered
    lines.append("\x1BE\x01" + "TOTAL A PAGAR".center(width) + "\x1BE\x00")
    
    # Large total amount (double height)
    large_total = format_amount(invoice.grand_total, include_currency=True)
    lines.append("\x1B!\x30" + large_total.center(width) + "\x1B!\x00")  # Double height + width
    
    lines.append("")
    lines.append(solid_line(width))
    lines.append("")
    
    # "Processado por Computador"
    lines.append("Processado por Computador".center(width))
    
    lines.append("")
    lines.append(dashed_line(width))
    lines.append("")
    
    # QR Code placeholder (future enhancement)
    if getattr(settings, "enable_qr_code", False):
        lines.append("[QR CODE]".center(width))
        lines.append("")
        lines.append(dashed_line(width))
        lines.append("")
    
    # Company contact information
    contact_parts = []
    if company_info["phone"]:
        contact_parts.append(company_info["phone"])
    if company_info["email"]:
        contact_parts.append(company_info["email"])
    
    if contact_parts:
        contact_line = " | ".join(contact_parts)
        lines.append(contact_line.center(width))
    
    # Custom footer (if configured)
    if settings.receipt_footer:
        lines.append("")
        lines.extend(format_custom_block(settings.receipt_footer, width))
    
    lines.append("")
    lines.append("")
    
    # Document status
    status_text = "**** FATURA FINAL ****" if invoice.docstatus == 1 else "**** FATURA RASCUNHO ****"
    lines.append(status_text.center(width))
    
    lines.append("\n\n\n")  # Feed before cut

    return [{"type": "raw", "data": "\n".join(lines)}]
