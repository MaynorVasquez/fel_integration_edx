import os

def crear_xml(xml_str, factura_name, carpeta, prefijo="dte_enviado"):
    ruta_script = os.path.dirname(os.path.abspath(__file__))
    ruta_padre = os.path.dirname(ruta_script)

    # Crear carpeta destino
    carpeta_destino = os.path.join(ruta_padre, carpeta)
    os.makedirs(carpeta_destino, exist_ok=True)

    # Nombre del archivo
    file_path = os.path.join(carpeta_destino, f"{prefijo}_{factura_name}.xml")

    # Guardar el XML crudo
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    # Verificar que el archivo exista y no esté vacío
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        raise Exception(f"El archivo {file_path} no se creó correctamente.")

    return file_path


