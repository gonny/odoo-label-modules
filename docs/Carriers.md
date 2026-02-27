## Czech post B2B API
- Full API documentation available at https://www.ceskaposta.cz/napi/b2b
- Also authentication mechanism, how to create HMAC signatures, Signing content signatures, etc.
- Testing keys, endpoints available see #Testovací účty in documentation
- Full code example in Javascript available

### Pickup points
- https://www.balikovna.cz/documents/20124/5404475/Bal%C3%ADkovna_widget_implementace.pdf/4dfae2f6-3972-90dd-4a26-4fbab49daebb?t=1719310469897
```
<iframe
title="Výběr místa pro vyzvednutí zásilky"
src=“https://b2c.cpost.cz/locations/?type=BALIKOVNY“
allow=“geolocation“ />
```

Result from Listener:
```
function iframeListener(event) {
if (event.data.message === ‚pickerResult‘) {
// Zpracovani event.data.point, pripadne event.data.
phone
// ...
}
}
window.addEventListener(‚message‘, iframeListener)
```

event.data output example:
```
„message“: „pickerResult“,
„id“: 123,
„point“: {
„id“: 123,
„type“: „BALIKOVNY“,
„zip“: „10000“,
„address“: „Černokostelecká 2020/20, Strašnice, 10000, Praha“,
„atm“: true,
„coor_x_wgs84“: „14.492777“,
„coor_y_wgs84“: „50.076442“,
„coords“: {„x“: 14.492777, „y“: 50.076442},
„distanceMeters“ : 1280.1306067886323,
„district“: „Hlavní město Praha“,
„municipality_district_name“: „Strašnice“,
„municipality_name“: „Praha“,
„name“: „Praha 10“,
„opening_hours“: [
 {„od_do“: [{„do“: „12:00“, „od“: „11:00“}, {„do“: „18:00“, „od“: „13:00“}]},
 {„od_do“: [{„do“: „12:00“, „od“: „11:00“}, {„do“: „18:00“, „od“: „13:00“}]},
 {„od_do“: [{„do“: „12:00“, „od“: „11:00“}, {„do“: „18:00“, „od“: „13:00“}]},
 {„od_do“: [{„do“: „12:00“, „od“: „11:00“}, {„do“: „18:00“, „od“: „13:00“}]},
 {„od_do“: [{„do“: „12:00“, „od“: „11:00“}, {„do“: „18:00“, „od“: „13:00“}]},
 „“,
 „“
 ],
„parking“: false,
„fulltext“: „10000 praha 10 hlavni mesto pra... /* zkraceno */“,
},
„phone“: „+420777123456“
}
```

**Fields**
- API Token
- Secret Key

---

## DPD API
- Documentation available at https://geoapi.dpd.cz/public-docs/cs/docs/api-usage
- Swagger - https://geoapi.dpd.cz/v2/swagger/ - There is also v1, but v2 is recommended. v2 may not have all features of v1. It needs to be checked.
- Throttling and other contraints described https://geoapi.dpd.cz/public-docs/cs/docs/api-usage
- Subject of implementation is to create Order in DPD system, get tracking number and print label. Save into ODOO in CRM. Be able to cancel DPD parcel if needed. Also, get tracking info and update ODOO CRM with it.

### Pickup points
- Pickup point selection widget - https://pickup.dpd.cz/integrace/
- Iframe integration with EventListener
- NOTICE! I Have no sample response!

```
<input id="DPDPickupPointResult" type="hidden"/>
  
  // tento kod vložte k inputu nebo do hlavičky () webu
  window.addEventListener("message", (event) => {
    if(event.data.dpdWidget) {
      document.getElementById("DPDPickupPointResult").value = event.data.dpdWidget.pickupPointResult
    } 
  }, false);
```
OR get result from EventListener directly without input field:
```
  window.addEventListener("message", (event) => {
    if(event.data.dpdWidget) {
      console.log(event.data.dpdWidget);
    }
  }, false);
```

**Configurable Fields**
- DPD_API_KEY
- DPD_API_DSW

---

## Packeta API
- Documentation available at https://docs.packeta.com/guides/introduction#own-integration
- Possible to check existing Odoo Packeta modules available from Gihub to get more details about implementation. 

### Pickup points
- Widget docuemtnation available at https://docs.packeta.com/guides/introduction#widget
- Detailed widget documentation available at https://docs.packeta.com/docs/pudo-delivery/widget (data structures, endpoints, responses, etc.)
- They provide an integration library for JavaScript - https://widget.packeta.com/v6/www/js/library.js

**Configurable Fields**
- PACKETA_API_KEY
- PACKETA_API_SECRET (Password)

---

## The implementation Flow
- Contact (CRM) - create Shipping address information for company /person  -> setting carrier (DPD, Packeta, Ceska Posta) -> Selecting pickup point (if needed - Packeta, DPD, Balikovna) -> In quotation in Order / Label managment we will create label based on the shipping contact information from the CRM (company / person ).
- Prerequisites: 
  - - Multiple shipping addresses configuration enabled in Odoo CRM. 
  - - Carrier configuration for DPD, Packeta, Ceska Posta. (API keys, Authorization keys, etc.) - see fields above.

- Components to be implemented:
  - Carrier configuration in Odoo (API keys, etc.)
  - Shipping address information in CRM (company / person)
  - Label management in Odoo (create label, print label, cancel label, etc.)
  - Integration with DPD API (create order, get tracking number, print label, cancel parcel, get tracking info)
  - Integration with Packeta API (create order, get tracking number, print label, cancel parcel, get tracking info)
  - Integration with Ceska Posta B2B API (create order, get tracking number, print label, cancel parcel, get tracking info)
  - Pickup point selection for all 3 of them ( Packeta, DPD, Balikovna)

### Open questions:
- Do we need full view of all labels send? Guess yes.
- Which implies also to have possibility to reprint label, cancel label, etc.
- Do we need to have possibility to create label without order? Guess no, but it needs to be confirmed. 

