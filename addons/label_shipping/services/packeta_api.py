import base64
import logging
import xml.etree.ElementTree as ET

import requests

_logger = logging.getLogger(__name__)

API_URL = "https://www.zasilkovna.cz/api/rest"


def _build_create_packet_xml(api_password, data, pickup_point_id=None):
    """Build createPacket XML body.

    Args:
        api_password: Packeta API password.
        data: dict with keys: number, name, surname, company, email, phone,
              value, currency, weight, eshop, and optionally
              carrier_service_code, street, city, zip.
        pickup_point_id: If set, PUDO delivery (addressId). If None, HD.

    Returns:
        XML string for createPacket request.
    """
    root = ET.Element("createPacket")
    ET.SubElement(root, "apiPassword").text = api_password

    attrs = ET.SubElement(root, "packetAttributes")
    ET.SubElement(attrs, "number").text = str(data.get("number", ""))
    ET.SubElement(attrs, "name").text = str(data.get("name", ""))
    ET.SubElement(attrs, "surname").text = str(data.get("surname", ""))
    ET.SubElement(attrs, "company").text = str(data.get("company", ""))
    ET.SubElement(attrs, "email").text = str(data.get("email", ""))
    ET.SubElement(attrs, "phone").text = str(data.get("phone", ""))

    if pickup_point_id:
        ET.SubElement(attrs, "addressId").text = str(pickup_point_id)
    else:
        ET.SubElement(attrs, "carrierId").text = str(
            data.get("carrier_service_code", "")
        )
        ET.SubElement(attrs, "street").text = str(data.get("street", ""))
        ET.SubElement(attrs, "city").text = str(data.get("city", ""))
        ET.SubElement(attrs, "zip").text = str(data.get("zip", ""))

    ET.SubElement(attrs, "cod").text = "0"
    ET.SubElement(attrs, "value").text = str(data.get("value", 0))
    ET.SubElement(attrs, "currency").text = str(data.get("currency", "CZK"))
    ET.SubElement(attrs, "weight").text = str(data.get("weight", 0.5))
    ET.SubElement(attrs, "eshop").text = str(data.get("eshop", ""))

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _parse_response(xml_text):
    """Parse Packeta XML response.

    Args:
        xml_text: XML response string.

    Returns:
        Tuple of (success: bool, data: dict or error message str).
        On success, data contains 'id', 'barcode', 'barcodeText'.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return False, f"XML parse error: {e}"

    status = root.findtext("status", "")
    if status == "ok":
        result = root.find("result")
        if result is not None:
            return True, {
                "id": result.findtext("id", ""),
                "barcode": result.findtext("barcode", ""),
                "barcodeText": result.findtext("barcodeText", ""),
            }
        return True, {}
    fault = root.findtext("fault", "Unknown error")
    return False, fault


def create_packet(api_password, data, pickup_point_id=None):
    """Create a packet via Packeta XML API.

    Args:
        api_password: Packeta API password.
        data: dict with packet attributes.
        pickup_point_id: Pickup point ID for PUDO, or None for HD.

    Returns:
        Tuple of (success: bool, result dict or error message str).
    """
    try:
        xml_body = _build_create_packet_xml(
            api_password,
            data,
            pickup_point_id,
        )
        _logger.info("Packeta API request: %s", xml_body)
        response = requests.post(
            API_URL,
            data=xml_body.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8"},
            timeout=30,
        )
        _logger.info(
            "Packeta API response: %s %s",
            response.status_code,
            response.text[:500],
        )
        if response.status_code == 200:
            return _parse_response(response.text)
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("Packeta API error: %s", e)
        return False, str(e)


def get_packet_label(api_password, packet_id):
    """Download PDF label for a packet via Packeta XML API.

    Args:
        api_password: Packeta API password.
        packet_id: Carrier packet ID (from createPacket response).

    Returns:
        Tuple of (success: bool, pdf_bytes or error message str).
    """
    try:
        root = ET.Element("packetLabelPdf")
        ET.SubElement(root, "apiPassword").text = api_password
        ET.SubElement(root, "packetId").text = str(packet_id)
        ET.SubElement(root, "format").text = "A6 on A6"
        ET.SubElement(root, "offset").text = "0"

        xml_body = ET.tostring(root, encoding="unicode", xml_declaration=True)
        _logger.info("Packeta API label request: %s", xml_body)
        response = requests.post(
            API_URL,
            data=xml_body.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8"},
            timeout=30,
        )
        _logger.info(
            "Packeta API label response: %s (content_length=%s)",
            response.status_code,
            len(response.text),
        )
        if response.status_code == 200:
            resp_root = ET.fromstring(response.text)
            status = resp_root.findtext("status", "")
            if status == "ok":
                b64_data = resp_root.findtext("result", "")
                if b64_data:
                    return True, base64.b64decode(b64_data)
                return False, "Empty label data in response"
            fault = resp_root.findtext("fault", "Unknown error")
            return False, fault
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("Packeta label download error: %s", e)
        return False, str(e)


def cancel_packet(api_password, packet_id):
    """Cancel a packet via Packeta XML API.

    Args:
        api_password: Packeta API password.
        packet_id: Carrier packet ID.

    Returns:
        Tuple of (success: bool, result dict or error message str).
    """
    try:
        root = ET.Element("cancelPacket")
        ET.SubElement(root, "apiPassword").text = api_password
        ET.SubElement(root, "packetId").text = str(packet_id)

        xml_body = ET.tostring(root, encoding="unicode", xml_declaration=True)
        _logger.info("Packeta API cancel request: %s", xml_body)
        response = requests.post(
            API_URL,
            data=xml_body.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8"},
            timeout=30,
        )
        _logger.info(
            "Packeta API cancel response: %s %s",
            response.status_code,
            response.text[:500],
        )
        if response.status_code == 200:
            return _parse_response(response.text)
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    except requests.RequestException as e:
        _logger.error("Packeta cancel error: %s", e)
        return False, str(e)
