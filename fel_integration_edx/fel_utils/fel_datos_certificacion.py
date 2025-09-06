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
