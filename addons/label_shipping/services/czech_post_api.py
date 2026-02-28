import base64
import hashlib
import hmac
import logging
import time
import uuid

import requests

_logger = logging.getLogger(__name__)

API_BASE_URL = "https://b2b.postaonline.cz/api/v1"


def _compute_auth_headers(api_key, secret_key, body_bytes):
    """Compute HMAC-SHA256 authentication headers for Czech Post B2B API.

    Args:
        api_key: Czech Post API key (Api-Token).
        secret_key: Czech Post HMAC secret key.
        body_bytes: Request body as bytes (for POST), empty bytes for GET.

    Returns:
        Dict of authentication headers.
    """
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    body_hash = hashlib.sha256(body_bytes).hexdigest()

    message = f"{body_hash};{timestamp};{nonce}"
    signature = base64.b64encode(
        hmac.new(
            secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    return {
        "Api-Token": api_key,
        "Authorization-Timestamp": timestamp,
        "Authorization-Content-SHA256": body_hash,
        "Authorization": (
            f'CP-HMAC-SHA256 nonce="{nonce}" signature="{signature}"'
        ),
        "Content-Type": "application/json",
    }


def create_shipment(api_key, secret_key, data):
    """Create a shipment via Czech Post B2B API.

    Args:
        api_key: Czech Post API key.
        secret_key: Czech Post HMAC secret key.
        data: dict with shipment data.

    Returns:
        Tuple of (success: bool, result dict or error message str).
    """
    try:
        import json
        body = json.dumps(data).encode("utf-8")
        headers = _compute_auth_headers(api_key, secret_key, body)
        response = requests.post(
            f"{API_BASE_URL}/shipments",
            data=body,
            headers=headers,
            timeout=30,
        )
        if response.status_code in (200, 201):
            return True, response.json()
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("Czech Post API error: %s", e)
        return False, str(e)


def get_shipment_label(api_key, secret_key, shipment_id):
    """Download PDF label for a shipment.

    Args:
        api_key: Czech Post API key.
        secret_key: Czech Post HMAC secret key.
        shipment_id: Shipment/tracking ID.

    Returns:
        Tuple of (success: bool, pdf_bytes or error message str).
    """
    try:
        headers = _compute_auth_headers(api_key, secret_key, b"")
        response = requests.get(
            f"{API_BASE_URL}/shipments/{shipment_id}/label",
            headers=headers,
            timeout=30,
        )
        if response.status_code == 200:
            return True, response.content
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("Czech Post label download error: %s", e)
        return False, str(e)


def get_shipment_tracking(api_key, secret_key, shipment_id):
    """Get tracking status for a shipment.

    Args:
        api_key: Czech Post API key.
        secret_key: Czech Post HMAC secret key.
        shipment_id: Shipment/tracking ID.

    Returns:
        Tuple of (success: bool, tracking_data dict or error message str).
    """
    try:
        headers = _compute_auth_headers(api_key, secret_key, b"")
        response = requests.get(
            f"{API_BASE_URL}/shipments/{shipment_id}/tracking",
            headers=headers,
            timeout=30,
        )
        if response.status_code == 200:
            return True, response.json()
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("Czech Post tracking error: %s", e)
        return False, str(e)


def cancel_shipment(api_key, secret_key, shipment_id):
    """Cancel a shipment.

    Args:
        api_key: Czech Post API key.
        secret_key: Czech Post HMAC secret key.
        shipment_id: Shipment/tracking ID.

    Returns:
        Tuple of (success: bool, result dict or error message str).
    """
    try:
        headers = _compute_auth_headers(api_key, secret_key, b"")
        response = requests.delete(
            f"{API_BASE_URL}/shipments/{shipment_id}",
            headers=headers,
            timeout=30,
        )
        if response.status_code in (200, 204):
            return True, {"status": "cancelled"}
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("Czech Post cancel error: %s", e)
        return False, str(e)
