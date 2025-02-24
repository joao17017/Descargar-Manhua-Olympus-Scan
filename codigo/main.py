#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import os
import time
import urllib.parse
import requests
import hashlib
import shutil
import concurrent.futures
import zipfile
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


#################################
# Funciones auxiliares para logs
#################################

def shorten_path(path, base_dir, max_len=80):
    """
    Retorna una versión 'corta' del path, relativa a base_dir si es posible.
    Si aun así es muy largo, se trunca a max_len.
    """
    try:
        rel = os.path.relpath(path, base_dir)
    except ValueError:
        # Si no se puede relajar, usamos tal cual
        rel = path
    # Truncar si excede max_len
    if len(rel) > max_len:
        return rel[:max_len] + "..."
    return rel

def shorten_url(url, max_len=60):
    """
    Si la URL supera max_len, se trunca para no saturar el log.
    Útil para imágenes. No para la URL del capítulo.
    """
    if len(url) > max_len:
        return url[:max_len] + "..."
    return url

#################################
# SECCIÓN: Interfaz Tkinter + Log
#################################

def append_log(text):
    log_text.configure(state="normal")
    log_text.insert(tk.END, text + "\n")
    log_text.see("end")
    log_text.update_idletasks()
    log_text.configure(state="disabled")

def on_closing():
    root.destroy()

root = tk.Tk()
root.title("Herramientas de procesamiento de cómics")
root.geometry("700x650")

# Configurar grid para que la ventana sea responsive
root.columnconfigure(0, weight=1)
for i in range(6):
    root.rowconfigure(i, weight=1)

######################################################
# (1) Sección: Nombre de la Serie
######################################################
frame_serie = ttk.LabelFrame(root, text="Nombre de la Serie")
frame_serie.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
frame_serie.columnconfigure(1, weight=1)

ttk.Label(frame_serie, text="Nombre de la serie:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
entry_serie = ttk.Entry(frame_serie, width=60)
entry_serie.grid(row=0, column=1, sticky="ew", padx=5, pady=2)


######################################################
# (2) Sección: Descargar Capítulos
######################################################
frame_descarga = ttk.LabelFrame(root, text="Descargar Capítulos")
frame_descarga.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
frame_descarga.columnconfigure(1, weight=1)

ttk.Label(frame_descarga, text="URL del capítulo actual:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
entry_url = ttk.Entry(frame_descarga, width=60)
entry_url.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

ttk.Label(frame_descarga, text="Número final de capítulo:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
entry_final = ttk.Entry(frame_descarga, width=20)
entry_final.grid(row=1, column=1, sticky="w", padx=5, pady=2)

def confirm_and_run_descargar():
    """
    1) Verifica que estén completos los campos (serie, URL, capítulo final).
    2) Muestra ventana "¿Está seguro de continuar?" con botones Sí/No.
       - Si No -> cierra la app.
       - Si Sí -> llama a run_descargar() para iniciar la descarga en un hilo.
    """
    serie_name = entry_serie.get().strip()
    url = entry_url.get().strip()
    final_chapter = entry_final.get().strip()

    # Validaciones previas
    if not serie_name:
        messagebox.showerror("Error", "Por favor, ingresa el nombre de la serie.")
        return
    if not url or not final_chapter:
        messagebox.showerror("Error", "Por favor, ingresa la URL y el número final de capítulo.")
        return

    # Mostrar alerta de confirmación
    respuesta = messagebox.askyesno("Confirmación", "¿Tiene una copia en fisico?")

    if respuesta:
        # Si elige Sí, iniciamos el hilo de descarga
        threading.Thread(
            target=descargar,
            args=(serie_name, url, final_chapter),
            daemon=True
        ).start()
    else:
        # Si elige No, se cierra toda la aplicación
        root.destroy()

btn_descargar = ttk.Button(frame_descarga, text="Iniciar Descarga", command=confirm_and_run_descargar)
btn_descargar.grid(row=2, column=0, columnspan=2, pady=5)


######################################################
# (3) Sección: Eliminar Duplicados de Imágenes
######################################################
frame_duplicados = ttk.LabelFrame(root, text="Eliminar Duplicados de Imágenes")
frame_duplicados.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

def run_eliminar_duplicados():
    serie_name = entry_serie.get().strip()
    if not serie_name:
        messagebox.showerror("Error", "Por favor, ingresa el nombre de la serie.")
        return

    threading.Thread(
        target=eliminar_duplicados_img,
        args=(serie_name,),
        daemon=True
    ).start()

btn_duplicados = ttk.Button(frame_duplicados, text="Eliminar Duplicados", command=run_eliminar_duplicados)
btn_duplicados.pack(padx=5, pady=5, anchor="w")


######################################################
# (4) Sección: Convertir Carpetas a CBZ
######################################################
frame_cbz = ttk.LabelFrame(root, text="Convertir Carpetas a CBZ")
frame_cbz.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
frame_cbz.columnconfigure(1, weight=1)

ttk.Label(frame_cbz, text="Prefijo para CBZ:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
entry_prefix = ttk.Entry(frame_cbz, width=30)
entry_prefix.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

def run_convertir_cbz():
    serie_name = entry_serie.get().strip()
    prefix = entry_prefix.get().strip()

    if not serie_name:
        messagebox.showerror("Error", "Por favor, ingresa el nombre de la serie.")
        return
    if not prefix:
        messagebox.showerror("Error", "Por favor, ingresa un prefijo para los archivos CBZ.")
        return

    threading.Thread(
        target=convertir_folder_a_cbz,
        args=(serie_name, prefix),
        daemon=True
    ).start()

btn_cbz = ttk.Button(frame_cbz, text="Convertir a CBZ", command=run_convertir_cbz)
btn_cbz.grid(row=1, column=0, columnspan=2, pady=5)


######################################################
# (5) Sección: Eliminar Carpetas y CBZ
######################################################
frame_eliminar = ttk.LabelFrame(root, text="Eliminar Carpetas y CBZ")
frame_eliminar.grid(row=4, column=0, sticky="ew", padx=10, pady=5)

def run_eliminar_archivos():
    serie_name = entry_serie.get().strip()
    if not serie_name:
        messagebox.showerror("Error", "Por favor, ingresa el nombre de la serie.")
        return

    threading.Thread(
        target=eliminar_archivos_al_finalizar,
        args=(serie_name,),
        daemon=True
    ).start()

btn_eliminar = ttk.Button(frame_eliminar, text="Eliminar Carpetas y CBZ", command=run_eliminar_archivos)
btn_eliminar.pack(padx=5, pady=5, anchor="w")


######################################################
# (6) Sección: Salida / Log
######################################################
frame_log = ttk.LabelFrame(root, text="Salida")
frame_log.grid(row=5, column=0, sticky="nsew", padx=10, pady=5)
frame_log.rowconfigure(0, weight=1)
frame_log.columnconfigure(0, weight=1)

log_text = scrolledtext.ScrolledText(frame_log, wrap=tk.WORD, state="disabled")
log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

root.protocol("WM_DELETE_WINDOW", on_closing)

##############################
# SECCIÓN: Funciones unificadas
##############################

def descargar(serie_name, url, final_chapter):
    """Descarga capítulos desde 'url' hasta 'final_chapter', guardando en:
       Nombre_de_la_serie/Capitulos_Carpetas/<nro_capítulo>/.
    """
    append_log(f"[DESCARGAR] Serie: {serie_name} | URL capítulo: {url} | Capítulo final: {final_chapter}")

    try:
        final_chapter_val = float(final_chapter)
    except ValueError:
        append_log("[DESCARGAR] Error: el capítulo final no es numérico.")
        return

    serie_dir = os.path.join(os.getcwd(), serie_name)
    capitulos_dir = os.path.join(serie_dir, "Capitulos_Carpetas")
    os.makedirs(capitulos_dir, exist_ok=True)

    # Carpeta caché
    TAMANIO_MIN = 40 * 1024
    cache_dir = os.path.join(serie_dir, "cache_images")
    os.makedirs(cache_dir, exist_ok=True)

    with sync_playwright() as p:
        next_url = url
        while next_url:
            # Mantenemos la URL completa del capítulo
            append_log(f"[DESCARGAR] Abriendo capítulo: {next_url}")
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            page.goto(next_url)

            chapter_number = _get_chapter_number(page)
            if chapter_number is None:
                chapter_number = "Desconocido"

            # Carpeta del capítulo (mostrarla en corto en log)
            chapter_folder = os.path.join(capitulos_dir, chapter_number)
            os.makedirs(chapter_folder, exist_ok=True)
            short_chapter_folder = shorten_path(chapter_folder, serie_dir)

            append_log(f"[DESCARGAR] Descargando imágenes en: {short_chapter_folder}")
            _download_images_from_page(page, chapter_folder, cache_dir, TAMANIO_MIN, serie_dir)

            # Ver si se alcanzó el capítulo final
            try:
                current_chapter_val = float(chapter_number)
            except ValueError:
                current_chapter_val = None

            if current_chapter_val and current_chapter_val >= final_chapter_val:
                append_log(f"[DESCARGAR] Alcanzado capítulo final {chapter_number}. Deteniendo.")
                browser.close()
                break

            next_url = _get_next_chapter_link(page)
            browser.close()
            time.sleep(2)

    append_log("[DESCARGAR] Descarga completada.\n")


def _get_chapter_number(page):
    """Extrae el número de capítulo en la etiqueta <b class="text-xs md:text-base">."""
    start_time = time.monotonic()
    time.sleep(1)
    while time.monotonic() - start_time < 5:
        try:
            elem = page.query_selector("b.text-xs.md\\:text-base")
            if elem:
                chapter_number = elem.inner_text().strip()
                append_log(f"[DESCARGAR] → Número de capítulo: {chapter_number}")
                return chapter_number
        except Exception as e:
            append_log(f"[DESCARGAR] Error extrayendo número de capítulo: {e}")
        time.sleep(0.25)
    append_log("[DESCARGAR] No se encontró el número de capítulo en 5 segundos.")
    return None


def _download_images_from_page(page, chapter_folder, cache_dir, min_size, serie_dir):
    """Descarga imágenes .webp del capítulo a 'chapter_folder'. Usa caché en 'cache_dir'."""
    last_count = 0
    attempts = 0
    while attempts < 5:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(3000)
        current_count = page.evaluate("() => document.querySelectorAll('img').length")
        append_log(f"[DESCARGAR] Scroll #{attempts+1}: {current_count} imágenes detectadas.")
        if current_count == last_count:
            break
        last_count = current_count
        attempts += 1

    image_elements = page.query_selector_all("img")
    image_urls = []
    for img in image_elements:
        src = img.get_attribute("src")
        if src and src.lower().endswith(".webp") and "/cover" not in src.lower() and "discus" not in src.lower():
            image_urls.append(src)

    append_log(f"[DESCARGAR] Se descargarán {len(image_urls)} imágenes (.webp).")

    with requests.Session() as session:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for idx, img_url in enumerate(image_urls, start=1):
                futures.append(
                    executor.submit(
                        _download_single_image,
                        session,
                        img_url,
                        chapter_folder,
                        idx,
                        page.url,
                        cache_dir,
                        min_size,
                        serie_dir
                    )
                )
            concurrent.futures.wait(futures)


def _download_single_image(session, img_url, chapter_folder, idx, page_url, cache_dir, min_size, serie_dir):
    """Descarga 1 imagen, guardándola en 'cache_dir'. Si >= min_size, se copia a 'chapter_folder'."""
    if not img_url.startswith("http"):
        img_url = urllib.parse.urljoin(page_url, img_url)

    short_img_url = shorten_url(img_url)  # Para no mostrar URL largas de imágenes
    try:
        ext = os.path.splitext(urllib.parse.urlparse(img_url).path)[1] or ".webp"
        url_hash = hashlib.sha256(img_url.encode('utf-8')).hexdigest()
        cache_filename = url_hash + ext
        cache_path = os.path.join(cache_dir, cache_filename)
        dest_filename = os.path.join(chapter_folder, f"imagen_{idx:03d}{ext}")

        # Rutas en corto
        short_cache_path = shorten_path(cache_path, serie_dir)
        short_dest_filename = shorten_path(dest_filename, serie_dir)

        # Verificar en caché
        if os.path.exists(cache_path):
            if os.path.getsize(cache_path) >= min_size:
                shutil.copy2(cache_path, dest_filename)
                append_log(f"[DESCARGAR] Usado caché: {short_dest_filename}")
                return
            else:
                os.remove(cache_path)

        # HEAD para ver tamaño aproximado
        try:
            head_resp = session.head(img_url, allow_redirects=True)
            if head_resp.status_code == 200 and "Content-Length" in head_resp.headers:
                size = int(head_resp.headers["Content-Length"])
                if size < min_size:
                    append_log(f"[DESCARGAR] Ignorando (pequeña) {short_img_url} ({size} bytes)")
                    return
        except Exception as e:
            append_log(f"[DESCARGAR] HEAD error con {short_img_url}: {e}")

        # Descarga
        resp = session.get(img_url, stream=True)
        if resp.status_code == 200:
            with open(cache_path, "wb") as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            downloaded_size = os.path.getsize(cache_path)
            if downloaded_size < min_size:
                os.remove(cache_path)
                return
            shutil.copy2(cache_path, dest_filename)
            append_log(f"[DESCARGAR] OK => {short_dest_filename} ({downloaded_size} bytes)")
        else:
            append_log(f"[DESCARGAR] Error {resp.status_code} descargando {short_img_url}")
    except Exception as e:
        append_log(f"[DESCARGAR] Error descargando {short_img_url}: {e}")


def _get_next_chapter_link(page):
    """
    Devuelve la URL completa del siguiente capítulo, o None si no lo encuentra.
    (Se asume que la URL completa sí debe ser visible).
    """
    try:
        next_link = page.wait_for_selector("a:has(i[class*='chevron-right'])", timeout=5000)
        if next_link:
            href = next_link.get_attribute("href")
            if href:
                return urllib.parse.urljoin(page.url, href)
    except Exception as e:
        append_log(f"[DESCARGAR] Error obteniendo link del siguiente capítulo: {e}")
    return None


def eliminar_duplicados_img(serie_name):
    """Elimina imágenes duplicadas en Nombre_de_la_serie/Capitulos_Carpetas."""
    append_log(f"[DUPLICADOS] Serie: {serie_name}. Buscando duplicados...")

    serie_dir = os.path.join(os.getcwd(), serie_name)
    capitulos_dir = os.path.join(serie_dir, "Capitulos_Carpetas")
    if not os.path.isdir(capitulos_dir):
        append_log("[DUPLICADOS] No existe la carpeta de capítulos. Cancelando.")
        return

    EXT_VALIDAS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}

    def calcular_hash(archivo):
        sha256 = hashlib.sha256()
        try:
            with open(archivo, "rb") as f:
                for data in iter(lambda: f.read(65536), b""):
                    sha256.update(data)
            return sha256.hexdigest()
        except Exception as e:
            short_a = shorten_path(archivo, serie_dir)
            append_log(f"[DUPLICADOS] Error en {short_a}: {e}")
            return None

    # hash -> [rutas...]
    hashes = {}
    for root, dirs, files in os.walk(capitulos_dir):
        if "cache_images" in dirs:
            dirs.remove("cache_images")
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in EXT_VALIDAS:
                ruta_completa = os.path.join(root, file)
                hval = calcular_hash(ruta_completa)
                if hval:
                    hashes.setdefault(hval, []).append(ruta_completa)

    # Eliminar duplicados (todas las copias)
    for hval, rutas in hashes.items():
        if len(rutas) > 1:
            for r in rutas:
                short_r = shorten_path(r, serie_dir)
                try:
                    os.remove(r)
                    append_log(f"[DUPLICADOS] Eliminado duplicado: {short_r}")
                except Exception as e:
                    append_log(f"[DUPLICADOS] Error al eliminar {short_r}: {e}")

    append_log("[DUPLICADOS] Proceso finalizado.\n")


def convertir_folder_a_cbz(serie_name, prefix):
    """
    Convierte cada subcarpeta de Nombre_de_la_serie/Capitulos_Carpetas
    en un archivo .cbz en Nombre_de_la_serie/comics_archivos/.
    """
    append_log(f"[CBZ] Serie: {serie_name} | Prefijo: {prefix}")

    serie_dir = os.path.join(os.getcwd(), serie_name)
    capitulos_dir = os.path.join(serie_dir, "Capitulos_Carpetas")
    comics_dir = os.path.join(serie_dir, "comics_archivos")

    if not os.path.isdir(capitulos_dir):
        append_log("[CBZ] No existe carpeta de capítulos. Cancelando.\n")
        return

    os.makedirs(comics_dir, exist_ok=True)

    EXT_VALIDAS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}

    for entry in os.scandir(capitulos_dir):
        if entry.is_dir():
            nombre_chapter = entry.name  # ej: "10"
            output_cbz = os.path.join(comics_dir, f"{prefix} {nombre_chapter}.cbz")

            short_cbz = shorten_path(output_cbz, serie_dir)
            append_log(f"[CBZ] Creando: {short_cbz} (desde carpeta '{nombre_chapter}')")

            archivos = sorted(
                f for f in os.listdir(entry.path)
                if os.path.splitext(f)[1].lower() in EXT_VALIDAS
            )
            if not archivos:
                append_log("[CBZ]  -> Sin imágenes válidas. Se omite esta carpeta.")
                continue

            try:
                with zipfile.ZipFile(output_cbz, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for archivo in archivos:
                        ruta_abs = os.path.join(entry.path, archivo)
                        zipf.write(ruta_abs, arcname=archivo)
                append_log(f"[CBZ]  -> OK: carpeta '{nombre_chapter}' empaquetada.")
            except Exception as e:
                append_log(f"[CBZ] Error creando {short_cbz}: {e}")

    append_log("[CBZ] Conversión finalizada.\n")


def eliminar_archivos_al_finalizar(serie_name):
    """
    Elimina:
      - TODAS las subcarpetas de Capitulos_Carpetas
      - TODOS los archivos .cbz en comics_archivos
      - (Opcional) la carpeta cache_images
    """
    append_log(f"[ELIMINAR] Serie: {serie_name}. Borrando carpetas y CBZ...")

    serie_dir = os.path.join(os.getcwd(), serie_name)
    capitulos_dir = os.path.join(serie_dir, "Capitulos_Carpetas")
    comics_dir = os.path.join(serie_dir, "comics_archivos")

    # 1) Borrar subcarpetas en Capitulos_Carpetas
    if os.path.isdir(capitulos_dir):
        for entry in os.scandir(capitulos_dir):
            if entry.is_dir():
                short_p = shorten_path(entry.path, serie_dir)
                try:
                    shutil.rmtree(entry.path)
                    append_log(f"[ELIMINAR] Borrada carpeta: {short_p}")
                except Exception as e:
                    append_log(f"[ELIMINAR] Error al borrar {short_p}: {e}")

    # 2) Borrar .cbz en comics_archivos
    if os.path.isdir(comics_dir):
        for entry in os.scandir(comics_dir):
            if entry.is_file() and entry.name.lower().endswith(".cbz"):
                short_f = shorten_path(entry.path, serie_dir)
                try:
                    os.remove(entry.path)
                    append_log(f"[ELIMINAR] Borrado archivo: {short_f}")
                except Exception as e:
                    append_log(f"[ELIMINAR] Error al borrar {short_f}: {e}")

    # 3) (Opcional) borrar carpeta cache_images si se desea
    # cache_path = os.path.join(serie_dir, "cache_images")
    # if os.path.isdir(cache_path):
    #     short_c = shorten_path(cache_path, serie_dir)
    #     try:
    #         shutil.rmtree(cache_path)
    #         append_log(f"[ELIMINAR] Borrada carpeta caché: {short_c}")
    #     except Exception as e:
    #         append_log(f"[ELIMINAR] Error al borrar {short_c}: {e}")

    append_log("[ELIMINAR] Proceso completado.\n")


#########################
# Iniciar la app de Tkinter
#########################
if __name__ == "__main__":
    root.mainloop()
