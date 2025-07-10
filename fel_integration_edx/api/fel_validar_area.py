from zeep import Client
from lxml import etree
from .fel_utils import get_fel_config

def validate_user():
    """
    Valida el usuario FEL según configuración guardada
    en el Doctype FEL Integration
    """
    # obtenemos la config
    fel_conf = get_fel_config()

    area = fel_conf["area"]
    password = fel_conf["contraseña"]
    #wsdl = fel_conf["url"] + "?WSDL"
    wsdl = "https://edx.yaesta.com.gt/edx/core.asmx?WSDL"

    client = Client(wsdl=wsdl)
    result = client.service.ValidateUser(
        Area=area,
        Password=password
    )

    # parsear el XML de respuesta
    root = etree.fromstring(result.encode("utf-8"))
    has_error = root.findtext(".//HasError")
    return_value = root.findtext(".//ReturnValue")
    text_data = root.findtext(".//TextData")

    return {
        "has_error": has_error,
        "return_value": return_value,
        "text_data": text_data
    }