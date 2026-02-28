import logging

import requests

_logger = logging.getLogger(__name__)

PROD_URL = "https://geoapi.dpd.cz/v1"
TEST_URL = "https://geoapi-test.dpd.cz/v1"


def _base_url(test_mode=False):
    """Return API base URL based on mode."""
    return TEST_URL if test_mode else PROD_URL


def _headers(api_key):
    """Return common headers with API key."""
    return {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }


def create_shipment(api_key, dsw, data, test_mode=False):
    """Create a shipment via DPD GeoAPI v1.

    Args:
        api_key: DPD API key.
        dsw: DPD DSW customer identifier.
        data: dict with shipment data (sender, receiver, parcels, services).
        test_mode: Use test API endpoint if True.

    Returns:
        Tuple of (success: bool, result dict or error message str).
    """
    try:
        url = f"{_base_url(test_mode)}/shipments"
        payload = dict(data)
        if "customer" not in payload:
            payload["customer"] = {"dsw": dsw}
        response = requests.post(
            url, json=payload, headers=_headers(api_key), timeout=30,
        )
        if response.status_code in (200, 201):
            result = response.json()
            return True, result
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("DPD API error: %s", e)
        return False, str(e)


def get_labels(api_key, parcel_ident, test_mode=False):
    """Download PDF label for a parcel via DPD GeoAPI v1.

    Args:
        api_key: DPD API key.
        parcel_ident: Parcel identifier string.
        test_mode: Use test API endpoint if True.

    Returns:
        Tuple of (success: bool, pdf_bytes or error message str).
    """
    try:
        url = f"{_base_url(test_mode)}/parcels/{parcel_ident}/labels"
        payload = {"printType": "pdf", "printFormat": "A6"}
        response = requests.post(
            url, json=payload, headers=_headers(api_key), timeout=30,
        )
        if response.status_code == 200:
            return True, response.content
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("DPD label download error: %s", e)
        return False, str(e)


def cancel_shipment(api_key, shipment_id, test_mode=False):
    """Cancel a shipment via DPD GeoAPI v1.

    Args:
        api_key: DPD API key.
        shipment_id: DPD shipment ID string.
        test_mode: Use test API endpoint if True.

    Returns:
        Tuple of (success: bool, result dict or error message str).
    """
    try:
        url = f"{_base_url(test_mode)}/shipments/{shipment_id}"
        response = requests.delete(url, headers=_headers(api_key), timeout=30)
        if response.status_code in (200, 204):
            return True, {"status": "cancelled"}
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("DPD cancel error: %s", e)
        return False, str(e)
