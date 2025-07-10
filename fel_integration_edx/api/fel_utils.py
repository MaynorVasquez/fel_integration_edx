import frappe
from frappe import _

def get_fel_config():
    fel = frappe.get_doc("FEL Integration", "FEL Integration")
    return {
        "area": fel.area,
        "contraseña": fel.contraseña,
        "url": fel.url,
        "afiliacion_iva": fel.afiliacion_iva,
        "nit_certificador": fel.nit_certificador,
        "razon_social": fel.razon_social,
        "nombre_comercial": fel.nombre_comercial,
        "nit_emisor": fel.nit_emisor,
        "correo_emisor": fel.correo_emisor,
        "pais": fel.pais
        
    }


def get_fel_serie(tipo_documento, establecimiento):
    """
    Busca la configuración de la serie según tipo de documento
    y establecimiento en FEL Series Electronicas
    """
    fel_series_doc = frappe.get_doc("FEL Series Electronicas", "FEL Series Electronicas")
    
    for row in fel_series_doc.series_electronicas:
        # validamos tipo_documento con startswith para permitir descripciones
        # y establecimiento exactamente
        if row.tipo_documento.startswith(tipo_documento) and row.establecimiento == establecimiento:
            return {
                "transaccion": row.transaccion,
                "tipo_documento": row.tipo_documento,
                "serie": row.series,
                "establecimiento": row.establecimiento,
                "nombre_establecimiento": row.nombre_establecimiento,
                "direccion": row.direccion,
                "departamento": row.departamento,
                "municipio": row.municipio,
                "codigo_postal": row.código_postal
            }    
    frappe.throw(
        f"No se encontró configuración de serie para tipo de documento '{tipo_documento}' "
        f"y establecimiento '{establecimiento}'"
    )

