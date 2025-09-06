import frappe
import os

def log_sincronizacion_xml(doctype, 
                           docname, 
                           status="Exitoso",
                           sales_invoice=None, 
                           authorization_number=None,
                           certification_timestamp=None, 
                           series=None, 
                           number=None,
                           xml_request_path=None, 
                           xml_response_path=None):

    try:
        if not doctype or not docname:
            frappe.log_error("No se especificó doctype o docname para log_sincronizacion_xml")
            return

        # Obtener documento existente o crear uno nuevo
        if frappe.db.exists(doctype, docname):
            doc = frappe.get_doc(doctype, docname)
        else:
            doc = frappe.new_doc(doctype)
            doc.name = docname

        # Asignar valores de campos simples
        doc.status = status
        doc.sales_invoice = sales_invoice
        doc.authorization_number = authorization_number
        doc.certification_timestamp = certification_timestamp
        doc.series = series
        doc.number = number

        # Adjuntar XML Request
        if xml_request_path and os.path.exists(xml_request_path):
            with open(xml_request_path, "rb") as f:
                file_request = frappe.get_doc({
                    "doctype": "File",
                    "file_name": os.path.basename(xml_request_path),
                    "attached_to_doctype": doctype,
                    "attached_to_name": docname,
                    "is_private": 1,
                    "content": f.read()
                })
            file_request.save(ignore_permissions=True)
            doc.xml_request = file_request.file_url

            # 🔥 Eliminar archivo temporal
            os.remove(xml_request_path)

        # Adjuntar XML Response
        if xml_response_path and os.path.exists(xml_response_path):
            with open(xml_response_path, "rb") as f:
                file_response = frappe.get_doc({
                    "doctype": "File",
                    "file_name": os.path.basename(xml_response_path),
                    "attached_to_doctype": doctype,
                    "attached_to_name": docname,
                    "is_private": 1,
                    "content": f.read()
                })
            file_response.save(ignore_permissions=True)
            doc.xml_response = file_response.file_url

            # 🔥 Eliminar archivo temporal
            os.remove(xml_response_path)

        # Guardar log
        doc.save(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Error en log_sincronizacion_xml para {doctype} {docname}: {str(e)}")


