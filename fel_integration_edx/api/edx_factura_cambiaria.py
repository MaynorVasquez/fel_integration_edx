import frappe
import traceback
from frappe import _
from .fel_utils import get_fel_config, get_fel_serie
from frappe.utils import now_datetime, strip_html
from zeep import Client
from lxml import etree
import html
from frappe.utils import now_datetime

def certificar_factura(doc, method):
    frappe.db.after_commit(lambda: ejecutar_certificacion(doc.name))

def ejecutar_certificacion(nombre_factura):
    factura = frappe.get_doc("Sales Invoice", nombre_factura)
    xml_generado = generar_xml_dte(factura)
    print(xml_generado)
    print("==================Iniciando certificacion====================================")
    resultado = enviar_xml_dte(xml_generado, tipo_documento="FACT")
    print(resultado)
    print("==================Fin de la certificacion====================================")


def certificar_factura_post_commit(docname):
    try:
        print(f"Se ejecutó registrar_envio_fel_post_commit para {docname}")
        factura = frappe.get_doc("Sales Invoice", {docname})
        xml_generado = generar_xml_dte(factura)
        resultado = enviar_xml_dte(xml_generado, tipo_documento="FACT")
        if resultado.get("status") == "success":
            # Guardar en el Doctype de certificación
            frappe.get_doc({
                "doctype": "FEL Certificacion Factura Cambiaria",
                "status": "Exitoso",
                "request": xml_generado,
                "response": resultado.get("xml_respuesta"),
                "sales_invoice": docname,
                "authorization_number": resultado.get("numero_autorizacion"),
                "certification_timestamp": resultado.get("fecha_certificacion"),
                "series": resultado.get("serie"),
                "number": resultado.get("numero")
            }).insert(ignore_permissions=True)

            # Actualizar campos personalizados (opcionalmente en background)
            frappe.db.set_value("Sales Invoice", docname, {
                "fel_numero_autorizacion": resultado.get("numero_autorizacion"),
                "fel_serie": resultado.get("serie"),
                "fel_numero": resultado.get("numero"),
                "fel_certificacion_fecha": resultado.get("fecha_certificacion")
            })

        else:
            # Registro en caso de error
            frappe.get_doc({
                "doctype": "FEL Certificacion Factura Cambiaria",
                "status": "Error",
                "request": xml_generado,
                "response": resultado.get("mensaje_error"),
                "sales_invoice": docname
            }).insert(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "FEL post-commit error")



def enviar_xml_dte(xml, tipo_documento=None):
    fel_conf = get_fel_config()
    wsdl = fel_conf["url"] + "?WSDL"
    client = Client(wsdl=wsdl)

    # Limpiar encabezado XML
    lines = xml.strip().splitlines()
    clean_xml = "\n".join(lines[1:] if lines[0].startswith("<?xml") else lines)
    document_content = clean_xml

    try:
        response = client.service.CreateDocumentWithCustomResponse(
            Area=fel_conf["area"],
            Password=fel_conf["contraseña"],
            DocumentType=tipo_documento,
            DocumentContent=document_content,
            Connector="Xslt",
            ConvertDocument=True,
            SignDocument=True,
            PrintDocument=True
        )
    except Exception as e:
        return {
            "status": "error",
            "mensaje_error": f"Error al conectarse al certificador: {e}",
            "xml_request": clean_xml
        }

    try:
        
        root = etree.fromstring(response.encode("utf-8"))
        textdata = root.findtext(".//TextData")
        print(f"Contedido de response============= {response}")
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
    print(f"incicio ========: {start}")
    end = textdata.find(end_tag) + len(end_tag)
    print(f"FIN ===========: {end}")
    


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

    return {
        "status": "success",
        "uuid": uuid,
        "serie": serie,
        "numero": numero,
        "fecha_certificacion": fecha_cert,
        "xml_response": dte_unescaped,
        "xml_request": clean_xml
    }



def generar_xml_dte(sales_invoice_doc):
    """
    Genera el XML FEL estructurado de forma compatible con la SAT,
    para Factura Cambiaria (FCAM).
    """
    fel_conf = get_fel_config()

    doc = frappe.get_doc("Sales Invoice", sales_invoice_doc)
    # 2. Obtener el nombre del perfil POS desde la factura
    pos_profile_name = doc.pos_profile
    # 3. Obtener el POS Profile completo
    pos_profile_doc = frappe.get_doc("POS Profile", pos_profile_name)
    # 4. Leer el campo custom_establecimiento_fel
    establecimiento = pos_profile_doc.custom_establecimiento_fel
    # 5 obtienen el numero de series de SAP
    series = pos_profile_doc.custom_series

    # 2. Obtener el código de cliente
    customer_code = doc.customer
    # 3. Obtener el Customer
    customer_doc = frappe.get_doc("Customer", customer_code)
    # 4. Obtener el campo custom_nit
    nit_cliente = customer_doc.custom_nit or "CF"
    # 5 Obtienen el codigo del cliente 
    cardcode = customer_doc.custom_cardcode

    # obtener serie
    serie_data = get_fel_serie("FCAM - Factura cambiaria", establecimiento)

    # fecha con zona horaria y sin microsegundos
    fecha_emision = now_datetime().strftime("%Y-%m-%dT%H:%M:%S-06:00")

    nombre_cliente = sales_invoice_doc.customer_name
    direccion_cliente = sales_invoice_doc.customer_address or "CIUDAD"
    total_factura = "%.6f" % float(sales_invoice_doc.grand_total)
    currency = sales_invoice_doc.currency


    # 1. Tomar la dirección completa con HTML
    direccion_raw = doc.address_display
    # 2. Limpiar etiquetas HTML
    direccion_clean = strip_html(direccion_raw).strip()
    # 3. Separar por saltos de línea
    partes = direccion_clean.split("\n")
    # 4. Asignar a variables según el orden
    direccion = partes[0] if len(partes) > 0 else ""
    municipio  = partes[1] if len(partes) > 1 else ""
    departamento = partes[2] if len(partes) > 2 else ""

    # items
    items_xml = ""
    linea = 1
    for item in sales_invoice_doc.items:
        cantidad = float(item.qty)
        precio_unitario = float(item.rate)
        total = float(item.amount)
        
        # según estándar:
        precio_linea = precio_unitario * cantidad
        
        base = total / 1.12
        impuesto = total - base
        
        monto_gravable = "%.6f" % base
        monto_impuesto = "%.6f" % impuesto
        precio_unitario_fmt = "%.6f" % precio_unitario
        precio_linea_fmt = "%.6f" % precio_linea
        cantidad_fmt = "%.6f" % cantidad
        total_fmt = "%.6f" % total

        items_xml += f"""
        <dte:Item NumeroLinea="{linea}" BienOServicio="B">
            <dte:Cantidad>{cantidad_fmt}</dte:Cantidad>
            <dte:UnidadMedida>UNI</dte:UnidadMedida>
            <dte:Descripcion>{item.item_name}</dte:Descripcion>
            <dte:PrecioUnitario>{precio_unitario_fmt}</dte:PrecioUnitario>
            <dte:Precio>{precio_linea_fmt}</dte:Precio>
            <dte:Descuento>0.000000</dte:Descuento>
            <dte:Impuestos>
                <dte:Impuesto>
                    <dte:NombreCorto>IVA</dte:NombreCorto>
                    <dte:CodigoUnidadGravable>1</dte:CodigoUnidadGravable>
                    <dte:MontoGravable>{monto_gravable}</dte:MontoGravable>
                    <dte:MontoImpuesto>{monto_impuesto}</dte:MontoImpuesto>
                </dte:Impuesto>
            </dte:Impuestos>
            <dte:Total>{total_fmt}</dte:Total>
            <dte:personalizado1>{item.item_code or ""}</dte:personalizado1>
            <dte:personalizado2>{item.item_name or ""}</dte:personalizado2>
            <dte:personalizado3>{item.stock_uom or ""}</dte:personalizado3>
            <dte:personalizado4/>
            <dte:personalizado5/>
            <dte:personalizado6/>
            <dte:personalizado7/>
            <dte:personalizado8/>
            <dte:personalizado9/>
            <dte:personalizado10/>
            <dte:personalizado11/>
            <dte:personalizado12/>
            <dte:personalizado13/>
            <dte:personalizado14/>
            <dte:personalizado15/>
        </dte:Item>
        """
        linea += 1
    
        # validación para mínimo un ítem
    if not items_xml.strip():
        frappe.throw(_("El documento no tiene ítems válidos para generar FEL."))

    total_impuestos = "%.6f" % (float(total_factura) - float(float(total_factura) / 1.12))

    # complementos (FCAM)
    complementos_xml = f"""
        <dte:Complementos>
            <dte:Complemento  NombreComplemento="GT_Complemento_Cambiaria.xsd" URIComplemento="http://www.sat.gob.gt/dte/fel/CompCambiaria/0.2.0">
                <cfc:AbonosFacturaCambiaria Version="1">
                <cfc:Abono>
                    <cfc:NumeroAbono>1</cfc:NumeroAbono>
                    <cfc:FechaVencimiento>{fecha_emision[:10]}</cfc:FechaVencimiento>
                    <cfc:MontoAbono>{total_factura}</cfc:MontoAbono>
                </cfc:Abono>
                </cfc:AbonosFacturaCambiaria>
            </dte:Complemento>
        </dte:Complementos>
    """

    # armar XML
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<dte:GTDocumento 
    xmlns:dte="http://www.sat.gob.gt/dte/fel/0.1.0"
    xmlns:cfc="http://www.sat.gob.gt/dte/fel/CompCambiaria/0.1.0"
    xmlns:cno="http://www.sat.gob.gt/face2/ComplementoReferenciaNota/0.1.0"
    xmlns:cex="http://www.sat.gob.gt/face2/ComplementoExportaciones/0.1.0"
    xmlns:cfe="http://www.sat.gob.gt/face2/ComplementoFacturaEspecial/0.1.0"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    Version="0.4">
  <dte:SAT ClaseDocumento="dte">
    <dte:DTE ID="DatosCertificados">
      <dte:DatosEmision ID="DatosEmision">
        <dte:DatosGenerales Tipo="{serie_data['tipo_documento'].split("-")[0].strip()}" FechaHoraEmision="{fecha_emision}" CodigoMoneda="{currency}"/>
        <dte:Emisor NITEmisor="{fel_conf['nit_emisor']}" NombreEmisor="{fel_conf['razon_social']}" CodigoEstablecimiento="{serie_data['establecimiento']}" NombreComercial="{fel_conf['nombre_comercial']}" CorreoEmisor="{fel_conf['correo_emisor']}" AfiliacionIVA="{fel_conf['afiliacion_iva'].split("-")[0].strip()}"> 
          <dte:DireccionEmisor>
            <dte:Direccion>{serie_data['direccion']}</dte:Direccion>
            <dte:CodigoPostal>{serie_data['codigo_postal']}</dte:CodigoPostal>
            <dte:Municipio>{serie_data['municipio'].upper()}</dte:Municipio>
            <dte:Departamento>{serie_data['departamento'].upper()}</dte:Departamento>
            <dte:Pais>{fel_conf['pais']}</dte:Pais>
          </dte:DireccionEmisor>
        </dte:Emisor>
        <dte:Receptor IDReceptor="{nit_cliente}" NombreReceptor="{nombre_cliente}" CorreoReceptor="{sales_invoice_doc.contact_email or 'no-definido@correo.com'}">
          <dte:DireccionReceptor>
            <dte:Direccion>{direccion}</dte:Direccion>
            <dte:CodigoPostal>01010</dte:CodigoPostal>
            <dte:Municipio>{municipio}</dte:Municipio>
            <dte:Departamento>{departamento}</dte:Departamento>
            <dte:Pais>GT</dte:Pais>
          </dte:DireccionReceptor>
        </dte:Receptor>
        <dte:Frases>
          <dte:Frase TipoFrase="1" CodigoEscenario="1"/>
          <dte:Frase TipoFrase="2" CodigoEscenario="1"/>
        </dte:Frases>
        <dte:Items>
            {items_xml}
        </dte:Items>
        <dte:Totales>
          <dte:TotalImpuestos>
            <dte:TotalImpuesto NombreCorto="IVA" TotalMontoImpuesto="{total_impuestos}"/>
          </dte:TotalImpuestos>
          <dte:GranTotal>{total_factura}</dte:GranTotal>
        </dte:Totales>
          {complementos_xml}
      </dte:DatosEmision>
    </dte:DTE>
    <dte:Personalizado>
      <dte:Personalizado1>pruebas</dte:Personalizado1>
      <dte:Personalizado10/>
      <dte:Personalizado11/>
      <dte:Personalizado12/>
      <dte:Personalizado13/>
      <dte:Personalizado14/>
      <dte:Personalizado15/>
      <dte:Personalizado16/>
      <dte:Personalizado17/>
      <dte:Personalizado18/>
      <dte:Personalizado19/>
      <dte:Personalizado2>{series}</dte:Personalizado2>
      <dte:Personalizado20/>
      <dte:Personalizado21/>
      <dte:Personalizado3>preueba</dte:Personalizado3>
      <dte:Personalizado4>prueba</dte:Personalizado4>
      <dte:Personalizado5>{cardcode}</dte:Personalizado5>
      <dte:Personalizado6>prueba</dte:Personalizado6>
      <dte:Personalizado7>prueba</dte:Personalizado7>
      <dte:Personalizado9>prueba</dte:Personalizado9>
    </dte:Personalizado>
  </dte:SAT>
</dte:GTDocumento>
"""
    return xml
