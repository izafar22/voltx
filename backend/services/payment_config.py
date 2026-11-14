"""Public merchant instructions only. Never accept customer-supplied QR URLs."""

import os
from urllib.parse import urlsplit


def valid_public_qr_url(url):
    if not isinstance(url, str) or not url:
        return False
    try:
        parsed = urlsplit(url)
        return bool(
            parsed.scheme == "https"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


def public_payment_instructions():
    url = os.getenv("RUSHX_UPI_QR_IMAGE_URL", "").strip()
    reviewed = os.getenv("RUSHX_UPI_QR_REVIEWED", "false").lower() == "true"
    return {
        "qr_image_url": url if reviewed and valid_public_qr_url(url) else None,
        "instructions": "Pay the exact outstanding amount using the RushX merchant QR or contact support for manual payment instructions. Payment is confirmed only after our team verifies receipt.",
    }
