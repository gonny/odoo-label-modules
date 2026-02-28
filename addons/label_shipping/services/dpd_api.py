import logging
import requests

_logger = logging.getLogger(__name__)

PROD_URL = "https://geoapi.dpd.cz"
TEST_URL = "https://geoapi-test.dpd.cz"


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
    """Create a shipment via DPD GeoAPI v2.

    Args:
        api_key: DPD API key.
        dsw: DPD DSW customer identifier.
        data: dict with shipment data (sender, receiver, parcels, services).
        test_mode: Use test API endpoint if True.

    Returns:
        Tuple of (success: bool, result dict or error message str).
    """
    try:
        url = f"{_base_url(test_mode)}/v2/shipments"
        payload = dict(data)
        if "customer" not in payload:
            payload["customer"] = {"ident": dsw}
        response = requests.post(
            url, json=[payload], headers=_headers(api_key), timeout=30,
        )
        if response.status_code in (200, 201):
            result = response.json()
            return True, result
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("DPD API error: %s", e)
        return False, str(e)


def get_labels(api_key, parcel_numbers, test_mode=False):
    """Download PDF labels for parcels.

    Args:
        api_key: DPD API key.
        parcel_numbers: List of parcel number strings.
        test_mode: Use test API endpoint if True.

    Returns:
        Tuple of (success: bool, pdf_bytes or error message str).
    """
    try:
        url = f"{_base_url(test_mode)}/v2/labels"
        payload = {"parcels": parcel_numbers, "printType": "pdf"}
        response = requests.post(
            url, json=payload, headers=_headers(api_key), timeout=30,
        )
        if response.status_code == 200:
            return True, response.content
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("DPD label download error: %s", e)
        return False, str(e)


def get_tracking(api_key, parcel_number, test_mode=False):
    """Get tracking status for a parcel.

    Args:
        api_key: DPD API key.
        parcel_number: DPD parcel number string.
        test_mode: Use test API endpoint if True.

    Returns:
        Tuple of (success: bool, tracking_data dict or error message str).
    """
    try:
        url = f"{_base_url(test_mode)}/v2/tracking/{parcel_number}"
        response = requests.get(url, headers=_headers(api_key), timeout=30)
        if response.status_code == 200:
            return True, response.json()
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("DPD tracking error: %s", e)
        return False, str(e)


def cancel_shipment(api_key, parcel_number, test_mode=False):
    """Cancel a shipment.

    Args:
        api_key: DPD API key.
        parcel_number: DPD parcel number string.
        test_mode: Use test API endpoint if True.

    Returns:
        Tuple of (success: bool, result dict or error message str).
    """
    try:
        url = f"{_base_url(test_mode)}/v2/shipments/{parcel_number}"
        response = requests.delete(url, headers=_headers(api_key), timeout=30)
        if response.status_code in (200, 204):
            return True, {"status": "cancelled"}
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("DPD cancel error: %s", e)
        return False, str(e)
