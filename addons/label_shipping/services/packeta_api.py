import logging
import requests

_logger = logging.getLogger(__name__)

API_BASE_URL = "https://www.zasilkovna.cz/api/rest"


def create_packet(api_key, api_password, data):
    """Create a packet (shipment) via Packeta REST API.

    Args:
        api_key: Packeta API key.
        api_password: Packeta API password.
        data: dict with packet data (number, name, surname, email, phone,
              addressId, value, weight, eshop).

    Returns:
        Tuple of (success: bool, result: dict or error message str).
    """
    try:
        payload = dict(data)
        payload["apiPassword"] = api_password
        response = requests.post(
            f"{API_BASE_URL}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if response.status_code in (200, 201):
            result = response.json()
            return True, result
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("Packeta API error: %s", e)
        return False, str(e)


def get_packet_label(api_key, api_password, packet_id):
    """Download PDF label for a packet.

    Args:
        api_key: Packeta API key.
        api_password: Packeta API password.
        packet_id: Packet ID / tracking number.

    Returns:
        Tuple of (success: bool, pdf_bytes or error message str).
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/packet/{packet_id}/label/pdf",
            params={"apiPassword": api_password},
            timeout=30,
        )
        if response.status_code == 200:
            return True, response.content
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("Packeta label download error: %s", e)
        return False, str(e)


def get_packet_tracking(api_key, api_password, packet_id):
    """Get tracking status for a packet.

    Args:
        api_key: Packeta API key.
        api_password: Packeta API password.
        packet_id: Packet ID / tracking number.

    Returns:
        Tuple of (success: bool, tracking_data dict or error message str).
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/packet/{packet_id}/tracking",
            params={"apiPassword": api_password},
            timeout=30,
        )
        if response.status_code == 200:
            return True, response.json()
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("Packeta tracking error: %s", e)
        return False, str(e)


def cancel_packet(api_key, api_password, packet_id):
    """Cancel a packet.

    Args:
        api_key: Packeta API key.
        api_password: Packeta API password.
        packet_id: Packet ID / tracking number.

    Returns:
        Tuple of (success: bool, result dict or error message str).
    """
    try:
        response = requests.delete(
            f"{API_BASE_URL}/packet/{packet_id}",
            params={"apiPassword": api_password},
            timeout=30,
        )
        if response.status_code in (200, 204):
            return True, {"status": "cancelled"}
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("Packeta cancel error: %s", e)
        return False, str(e)
