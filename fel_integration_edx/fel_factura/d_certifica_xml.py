import frappe
from frappe import _
from fel_integration_edx.config.fel_datos_certificacion import get_fel_config
from zeep import Client
import requests

def enviar_xml_dte(xml, tipo_documento="FCAM"):
    fel_conf = get_fel_config()
    wsdl = fel_conf["url"]
    client = Client(wsdl=wsdl)
    document_content = xml.strip()
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
        return str(response)

    except Exception as e:
        raise Exception(f"Error al conectarse al certificador: {e}")

# def enviar_xml_dte(xml, tipo_documento="FCAM"):
#     fel_conf = get_fel_config()
#     wsdl = fel_conf["url"]
#     client = Client(wsdl=wsdl)
#     document_content = xml.strip()
#     try:
#         response = client.service.CreateDocumentWithCustomResponse(
#             Area=fel_conf["area"],
#             Password=fel_conf["contraseña"],
#             DocumentType=tipo_documento,
#             DocumentContent=document_content,
#             Connector="Xslt",
#             ConvertDocument=True,
#             SignDocument=True,
#             PrintDocument=True
#         )

#         return str(response)

#     except Exception as e:
#         return f"<error>Error al conectarse al certificador: {e}</error>"
