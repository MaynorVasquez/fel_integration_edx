from lxml import etree
import html

def procesar_dte(response):
    try:
        
        root = etree.fromstring(response.encode("utf-8"))
        textdata = root.findtext(".//TextData")
    except Exception as e:
        return {
            "status": "error",
            "mensaje_error": f"Respuesta inválida del certificador: {e}",
            "Error": "error 1"
        }
    # Procesar CDATA
    start_tag = "<DTE>"
    end_tag = "</DTE>"
    start = textdata.find(start_tag)
    end = textdata.find(end_tag) + len(end_tag)

    dte_escaped = textdata[start + len(start_tag): end - len(end_tag)]

    # 5. Desescapar entidades HTML/XML
    dte_unescaped = html.unescape(dte_escaped.strip())

    try:
        cert_root = etree.fromstring(dte_unescaped.encode("utf-8"))
    except Exception as e:
        return {
            "status": "error",
            "mensaje_error": f"No se pudo parsear el XML certificado: {e}",
            "Error": dte_unescaped
        }
    
    ns = {"dte": "http://www.sat.gob.gt/dte/fel/0.2.0"}
    uuid = cert_root.findtext(".//dte:NumeroAutorizacion", namespaces=ns)
    numero_autorizacion = cert_root.find(".//dte:NumeroAutorizacion", namespaces=ns)
    serie = numero_autorizacion.attrib.get("Serie", "") if numero_autorizacion is not None else ""
    numero = numero_autorizacion.attrib.get("Numero", "") if numero_autorizacion is not None else ""
    fecha_cert = cert_root.findtext(".//dte:FechaHoraCertificacion", namespaces=ns)
    # Dirección del Emisor
    direccion_emisor = cert_root.findtext(".//dte:DireccionEmisor/dte:Direccion", namespaces=ns)

    # Obtener nodo Emisor
    emisor = cert_root.find(".//dte:Emisor", namespaces=ns)

    codigo_establecimiento = ""
    if emisor is not None:
        codigo_establecimiento = emisor.attrib.get("CodigoEstablecimiento", "")


    # Generar XML formateado
    xml_formateado = etree.tostring(
        cert_root,
        pretty_print=True,
        encoding="utf-8",
        xml_declaration=True
    ).decode("utf-8")


    # archivo_salida = "/home/frappe/smart/apps/fel_integration_edx/fel_integration_edx/xml_generados/xml_respuesta.xml"
    # # Guardar en archivo si se proporciona ruta
    # if archivo_salida:
    #     with open(archivo_salida, "w", encoding="utf-8") as f:
    #         f.write(xml_formateado)

    return {
        "status": "success",
        "uuid": uuid,
        "serie": serie,
        "numero": numero,
        "fecha_certificacion": fecha_cert,
        "direccion_emisor": direccion_emisor,
        "codigo_establecimiento": codigo_establecimiento,
        "xml_formateado": xml_formateado
    }