from fel_integration_edx.api.edx_factura_cambiaria import generar_xml_dte
from fel_integration_edx.api.edx_factura_cambiaria import enviar_xml_dte
doc = frappe.get_doc("Sales Invoice", "ACC-SINV-2025-00064")
result = generar_xml_dte(doc)
resultado = enviar_xml_dte(result, tipo_documento="FCAM")



##imprimir xml 
from xml.dom import minidom
xml_pretty = minidom.parseString(result).toprettyxml(indent="  ")
print(xml_pretty)


##parceo de xml archivo respuesta certificador
from lxml import etree
import html

ruta = os.path.join(frappe.get_app_path("fel_integration_edx"), "api", "factura.txt")

with open(ruta, "r", encoding="utf-8") as f:
    response = f.read()
	
# 2. Parsear el XML externo (el <ProcessResult>)
root = etree.fromstring(response.encode("utf-8"))

# 3. Extraer el contenido del CDATA dentro de <TextData>
text_data = root.findtext(".//TextData")

# 4. Ahora extraemos el contenido que está entre <DTE> y </DTE> (todavía está escapado)
start_tag = "<DTE>"
end_tag = "</DTE>"


start = text_data.find(start_tag)
end = text_data.find(end_tag) + len(end_tag)


dte_escaped = text_data[start + len(start_tag): end - len(end_tag)]

# 5. Desescapar entidades HTML/XML
dte_unescaped = html.unescape(dte_escaped.strip())

# 6. Parsear como XML
try:
    cert_root = etree.fromstring(dte_unescaped.encode("utf-8"))
except Exception as e:
    frappe.throw(f"No se pudo parsear el XML certificado: {e}")
	
# 7. Extraer datos del XML ya certificado
ns = {"dte": "http://www.sat.gob.gt/dte/fel/0.2.0"}
uuid = cert_root.findtext(".//dte:NumeroAutorizacion", namespaces=ns)
serie = cert_root.find(".//dte:NumeroAutorizacion", namespaces=ns).get("Serie")
numero = cert_root.find(".//dte:NumeroAutorizacion", namespaces=ns).get("Numero")
fecha_cert = cert_root.findtext(".//dte:FechaHoraCertificacion", namespaces=ns)

print("UUID:", uuid)
print("Serie:", serie)
print("Número:", numero)
print("Fecha Certificación:", fecha_cert)