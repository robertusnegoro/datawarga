def format_rupiah(val):
    """
    Formats a numeric value into Indonesian Rupiah style with dot thousand separators.
    Example: 150000 -> "Rp 150.000"
             -50000 -> "- Rp 50.000"
    """
    if val is None:
        return "Rp 0"
    try:
        val_int = int(val)
        if val_int < 0:
            return f"- Rp {abs(val_int):,}".replace(",", ".")
        return f"Rp {val_int:,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(val)
