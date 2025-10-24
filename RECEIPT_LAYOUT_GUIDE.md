# NextPOS Printing - Receipt Layout Guide

## Overview

The receipt layout has been refactored to produce professional 80mm thermal receipts matching Mozambican business standards with proper formatting, structure, and ESC/POS commands.

---

## Receipt Structure

### 1. **Header Section**
- **Company Name** (Bold, centered)
- **Company Address** (Centered)
- **Company NUIT** (Tax ID, centered)

```
         MozEconomia, SA
  Avenida 25 de Setembro, 1234 — Maputo
            NUIT: 400567890
```

### 2. **Customer Information Section**
- **Cliente:** Customer name
- **NUIT:** Customer tax ID (if available)
- **Data:** Date and time (dd/MM/yyyy HH:mm format)
- **Fatura Nº:** Invoice number

```
Cliente: João Carlos Comércio, Lda
NUIT: 123456789
Data: 24/10/2025 10:42
Fatura Nº: FT-2025-0017
```

### 3. **Items Table**
Three-column format with headers:
- **Descrição** (60% width) - Item description
- **Qtd** (10% width) - Quantity
- **Valor** (30% width) - Amount

```
Descricao                        Qtd        Valor
HP ProBook 460 G11                 1    56,000.00
Impressora Térmica 80mm            1     8,450.00
```

### 4. **Totals Section**
- **Sub-total** - Net total before taxes
- **IVA 16%** (or other tax descriptions)
- **TOTAL** (Bold) - Grand total

```
Sub-total                        72,250.00 MZN
IVA 16%                          11,560.00 MZN
TOTAL                            83,810.00 MZN
```

### 5. **Payment Section**
- **Pagamento:** Payment method (e.g., M-Pesa, Dinheiro, Visa)
- **Ref.:** Payment reference (if available)
- **Troco:** Change amount (if applicable)

```
Pagamento: M-Pesa
Ref.: MP-20251024-1042
```

### 6. **Footer Section**
- **"TOTAL A PAGAR"** (Bold, centered)
- **Large Total Amount** (Double height, centered)
- **Solid separator line**
- **"Processado por Computador"**
- **QR Code placeholder** (optional, if enabled)
- **Company contact info** (Phone | Email)
- **Custom footer text** (if configured)
- **Document status** (FATURA FINAL / FATURA RASCUNHO)

```
          TOTAL A PAGAR
         83,810.00 MZN
================================================
     Processado por Computador
------------------------------------------------
            [QR CODE]
------------------------------------------------
  +258 84 444 4645 | cloud@mozeconomia.co.mz
------------------------------------------------
        **** FATURA FINAL ****
```

---

## Configuration

### NextPOS Settings

#### Paper Width
- **Default:** 48 characters (for 80mm thermal)
- **Options:** 42 (58mm), 48 (80mm), 80 (A4)

**Path:** NextPOS Settings → Printing Settings → Paper Width

#### Enable QR Code
Enable QR code placeholder in footer.

**Path:** NextPOS Settings → Receipt Layout → Enable QR Code

---

## Technical Details

### ESC/POS Commands Used

| Command | Hex | Purpose |
|---------|-----|---------|
| `\x1BE\x01` | ESC E 1 | Enable bold/emphasized text |
| `\x1BE\x00` | ESC E 0 | Disable bold |
| `\x1B!\x30` | ESC ! 48 | Double height + double width |
| `\x1B!\x00` | ESC ! 0 | Normal text size |

### Column Width Calculations

For 80mm thermal (48 characters):
- **Description column:** 60% = 28 characters
- **Quantity column:** 10% = 4 characters  
- **Value column:** 30% = 14 characters

### Amount Formatting

All amounts use comma thousands separator:
- `56,000.00` (not `56000.00`)
- `83,810.00 MZN` (with currency suffix)

---

## Data Sources

### Company Information
- **Name:** `invoice.company` → Company DocType
- **Address:** Retrieved from linked Address DocType
- **Tax ID (NUIT):** `company.tax_id`
- **Phone:** `company.phone_no`
- **Email:** `company.email`

### Customer Information
- **Name:** `invoice.customer_name` or `invoice.customer`
- **Tax ID (NUIT):** `customer.tax_id`

### Invoice Data
- **Date/Time:** `invoice.posting_date` (formatted as dd/MM/yyyy HH:mm)
- **Invoice Number:** `invoice.name`
- **Items:** `invoice.items[]` (item_name, qty, amount)
- **Subtotal:** `invoice.net_total` or `invoice.total`
- **Taxes:** `invoice.taxes[]` (description, tax_amount)
- **Grand Total:** `invoice.grand_total`

### Payment Information
- **Payment Method:** `invoice.payments[0].mode_of_payment`
- **Reference:** `invoice.payments[0].reference_no`
- **Change:** `invoice.change_amount`

---

## Customization Points

### 1. Add Company Logo
Add ESC/POS image commands before header:

```python
# In render_invoice(), before header section
if settings.get("show_logo"):
    logo_escpos = generate_company_logo_escpos(invoice.company)
    lines.append(logo_escpos)
    lines.append("")
```

### 2. Add QR Code with Invoice Data
Replace QR code placeholder with actual ESC/POS QR command:

```python
# Replace lines 263-268 with:
if settings.get("enable_qr_code"):
    qr_data = f"Invoice:{invoice.name}|Total:{invoice.grand_total}|Date:{invoice.posting_date}"
    qr_command = generate_qr_code_escpos(qr_data)
    lines.append(qr_command)
    lines.append("")
```

### 3. Multi-line Item Descriptions
Wrap long item names across multiple lines:

```python
# In items section (line 191)
item_lines = wrap_text(item.item_name, col1_width)
for idx, line in enumerate(item_lines):
    if idx == 0:
        # First line with qty and amount
        item_row = format_table_row(line, qty_str, amount_str, width, col1_width, col2_width)
    else:
        # Continuation lines (description only)
        item_row = format_table_row(line, "", "", width, col1_width, col2_width)
    lines.append(item_row)
```

### 4. Show Item Rates
Add rate per unit under each item:

```python
# After line 196
lines.append(f"   @ {format_amount(item.rate)} x {item.qty:.0f}")
```

### 5. Add Cashier Information
Include cashier in footer:

```python
# After payment section (line 242)
if settings.show_cashier and getattr(invoice, "owner", None):
    user = frappe.get_doc("User", invoice.owner)
    cashier_name = user.full_name or user.username
    lines.append(f"Operador: {cashier_name}")
```

---

## Portuguese Terminology

| English | Portuguese (Mozambique) |
|---------|------------------------|
| Customer | Cliente |
| Tax ID | NUIT |
| Date | Data |
| Invoice No. | Fatura Nº |
| Description | Descrição |
| Quantity | Qtd |
| Value | Valor |
| Sub-total | Sub-total |
| VAT | IVA |
| Total | TOTAL |
| Payment | Pagamento |
| Reference | Ref. |
| Change | Troco |
| Total to Pay | TOTAL A PAGAR |
| Computer Processed | Processado por Computador |
| Final Invoice | FATURA FINAL |
| Draft Invoice | FATURA RASCUNHO |

---

## Testing

### 1. Test with Sample Data

```bash
# From Frappe bench directory
bench --site [your-site] console
```

```python
from nextpos_printing.printing.receipt import render_invoice

# Test with existing POS Invoice
result = render_invoice("POS-INV-2025-00017")
print(result[0]["data"])
```

### 2. Visual Inspection Checklist

✅ Company name is bold and centered  
✅ Customer NUIT displays correctly  
✅ Date format is dd/MM/yyyy HH:mm  
✅ Items align in 3 columns  
✅ Amounts have comma separators  
✅ Taxes show with descriptions  
✅ TOTAL is bold  
✅ Payment method displays  
✅ Large total in footer  
✅ Contact info is centered  
✅ Document status shows correctly  

### 3. Printer Testing

1. Go to **NextPOS Settings**
2. Set **Paper Width** to **48**
3. Click **Print Test Receipt**
4. Verify physical print quality

---

## Migration from Old Layout

### Changes Summary

| Old Layout | New Layout |
|------------|------------|
| Custom header text only | Company info from database |
| No customer section | Dedicated customer section |
| Item name + qty × rate | 3-column table format |
| Simple tax list | Formatted sub-total + taxes |
| Single TOTAL line | Totals section with bold |
| Paid/Change only | Payment method + reference |
| Simple footer | Large total + contact info |
| English labels | Portuguese (Mozambican) |

### Settings Migration

No action required. Existing settings remain compatible:
- `receipt_header` - Now ignored (uses company data)
- `receipt_footer` - Still works (appears before status)
- `show_tax` - Still controls tax display
- `paper_width` - Default changed to 48

---

## Troubleshooting

### Issue: Company address not showing
**Solution:** Link an Address to the Company in ERPNext.

**Steps:**
1. Go to **Address List**
2. Create/edit address
3. Add **Dynamic Link**: Link DocType = "Company", Link Name = [Your Company]

### Issue: Customer NUIT not showing
**Solution:** Add tax_id field to Customer.

**Steps:**
1. Go to **Customer** form
2. Set **Tax ID** field
3. Save

### Issue: Columns misaligned
**Solution:** Verify paper width setting.

**Steps:**
1. Go to **NextPOS Settings**
2. Check **Paper Width** = 48 for 80mm thermal
3. Test print

### Issue: Amounts not formatted with commas
**Solution:** Check Python locale settings (handled automatically).

### Issue: Date shows as "dd-MM-yyyy" instead of "dd/MM/yyyy"
**Solution:** Code uses correct format. Check Frappe date settings if issues persist.

---

## Future Enhancements

### Planned Features
- [ ] QR Code generation with invoice validation data
- [ ] Company logo printing (ESC/POS image format)
- [ ] Multi-language support (PT/EN toggle)
- [ ] Item-level discounts display
- [ ] Loyalty points information
- [ ] Return/exchange notice
- [ ] Fiscal device integration (SAF-T AO)

### Advanced Customizations
- Conditional layouts based on customer type
- Department-specific receipt formats  
- Promotional banner rotation
- Digital receipt email integration

---

## Support

For technical assistance with receipt customization:
- **Developer:** ERPNext Specialist
- **Repository:** nextpos_printing custom app
- **Documentation:** This file + `README.md`

---

**Last Updated:** October 24, 2025  
**Version:** 2.0 (80mm Thermal Layout)

