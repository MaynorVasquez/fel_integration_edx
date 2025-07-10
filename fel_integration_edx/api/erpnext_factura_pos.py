import frappe
from .edx_factura_cambiaria import generar_xml_dte, enviar_xml_dte

def registrar_envio_fel_post_commit(doc, method):
    print(f"Se ejecutó registrar_envio_fel_post_commit para {doc.name}")

    if not hasattr(frappe.local, "after_commit"):
        frappe.local.after_commit = []

    # Encolar un job para ejecutar después del commit
    frappe.local.after_commit.append(
        lambda: frappe.enqueue(
            "fel_integration_edx.api.erpnext_factura_pos.procesar_fel",
            invoice_name=doc.name,
            queue='short'
        )
    )

def certificar_factura(doc, method):
    try:
        print(f"Se ejecutó registrar_envio_fel_post_commit para {doc.name}")
        factura = frappe.get_doc("Sales Invoice", {doc.name})
        xml_generado = generar_xml_dte(factura)
        print("=====================XML ENVIADO=================================================")
        print(xml_generado)
        print("======================================================================")
        resultado = enviar_xml_dte(xml_generado, tipo_documento="FACT")
        print("======================Respuesta del certifiacdor================================================")
        print(resultado)
        if resultado.get("status") == "success":
            # Guardar en el Doctype de certificación
            frappe.get_doc({
                "doctype": "FEL Certificacion Factura Cambiaria",
                "status": "Exitoso",
                "request": xml_generado,
                "response": resultado.get("xml_respuesta"),
                "sales_invoice": doc.name,
                "authorization_number": resultado.get("numero_autorizacion"),
                "certification_timestamp": resultado.get("fecha_certificacion"),
                "series": resultado.get("serie"),
                "number": resultado.get("numero")
            }).insert(ignore_permissions=True)

            # Actualizar campos personalizados (opcionalmente en background)
            frappe.db.set_value("Sales Invoice", doc.name, {
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
                "sales_invoice": doc.name
            }).insert(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "FEL post-commit error")
