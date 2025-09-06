import frappe
from frappe import _


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
                #"serie": row.series,
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

