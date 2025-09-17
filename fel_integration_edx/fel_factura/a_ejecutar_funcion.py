import frappe
from frappe import _
import os
from datetime import datetime
from fel_integration_edx.fel_factura.b_generar_xml import generar_xml_dte
from fel_integration_edx.fel_factura.c_crea_archivo_xml import crear_xml
from fel_integration_edx.fel_factura.d_certifica_xml import enviar_xml_dte
from fel_integration_edx.fel_factura.e_procesar_dte import procesar_dte
from fel_integration_edx.fel_logs.fel_logs import log_sincronizacion_xml
from fel_integration_edx.config.usuarios_autorizados import verificar_autorizacion


def enviar_xml(doc, method):
    try:

        usuario_actual = frappe.session.user
        doctype_actual = doc.doctype  # Ej: "Sales Invoice"

        # Verificar autorización
        if not verificar_autorizacion(usuario_actual, doctype_actual):
            print(f"El usuario {usuario_actual} no enviara el documento a sap tipo  {doctype_actual}")
            #frappe.msgprint(f"⚠ El usuario {usuario_actual} no está autorizado para sincronizar {doctype_actual} con SAP")
            return
        
        # 1. Generar XML
        xml = generar_xml_dte(doc.name)

        # 2. Guardar archivo en xml_request
        file_path_request = crear_xml(xml, doc.name, "xml_request", "FCAM")

        # 3. Leer archivo recién creado
        with open(file_path_request, "r", encoding="utf-8") as f:
            xml = f.read()

        # 4. Enviar al certificador
        response_xml = enviar_xml_dte(xml, tipo_documento="FCAM")
        datos_certificacion = procesar_dte(response_xml)

        if datos_certificacion.get("status") == "success":
            fecha_iso = datos_certificacion.get("fecha_certificacion")
            # Parsear ISO 8601
            fecha_obj = datetime.fromisoformat(fecha_iso)
            # Convertir a formato compatible con ERPNext (YYYY-MM-DD HH:MM:SS)
            fecha = fecha_obj.strftime("%Y-%m-%d %H:%M:%S")
            uuid = datos_certificacion.get("uuid")
            serie = datos_certificacion.get("serie")
            numero = datos_certificacion.get("numero")
            codigo_establecimiento = datos_certificacion.get("codigo_establecimiento")
            direccion_establecimiento = datos_certificacion.get("direccion_emisor")
            frappe.db.set_value("Sales Invoice", doc.name, "custom_uuid", uuid)
            frappe.db.set_value("Sales Invoice", doc.name, "custom_serie", serie)
            frappe.db.set_value("Sales Invoice", doc.name, "custom_numero", numero)
            frappe.db.set_value("Sales Invoice", doc.name, "custom_fecha", fecha)
            frappe.db.set_value("Sales Invoice", doc.name, "custom_establecimiento", codigo_establecimiento)
            frappe.db.set_value("Sales Invoice", doc.name, "custom_direccion_establecimiento", direccion_establecimiento)
            frappe.db.commit()
            
            # Guardar XML de respuesta
            file_path_response = crear_xml(datos_certificacion["xml_formateado"], doc.name, "xml_response", "FCAM")

            # guarda historian en el doctype logs
            log_sincronizacion_xml("FEL Certificacion Factura Cambiaria", 
                           docname=uuid, 
                           status="Exitoso",
                           sales_invoice= doc.name, 
                           authorization_number=uuid,
                           certification_timestamp=fecha, 
                           series=serie, 
                           number=numero,
                           xml_request_path=file_path_request, 
                           xml_response_path=file_path_response)

            # Mostrar modal de éxito
            frappe.msgprint(
                msg=_(f"Documento {doc.name} certificado correctamente.<br>UUID: {uuid}"),
                title=_("Éxito"),
                indicator="green"
            )
        else:
            # ❌ Error en certificación → cancelar transacción
            frappe.db.rollback()
            error_msg = datos_certificacion.get("error") or "Error desconocido"

            # Mostrar modal de error
            frappe.msgprint(
                msg=_(f"El documento {doc.name} no pudo ser certificado.<br>Respuesta: {error_msg}"),
                title=_("Error en Certificación"),
                indicator="red"
            )
            raise Exception("Error en certificación")

    except Exception as e:
        frappe.db.rollback()
        frappe.msgprint(
            _("Error crítico al certificar el documento {0}: {1}. El registro no se guardó.").format(doc.name, str(e)),
            alert=True,
            indicator="red"
        )
        frappe.log_error(frappe.get_traceback(), "Error en enviar_xml")
        raise

