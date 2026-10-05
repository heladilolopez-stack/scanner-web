from flask import (
    Flask,
    render_template,
    request,
    send_file,
    jsonify
)

import subprocess
import img2pdf
from datetime import datetime
from pathlib import Path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

BASE_FOLDER = Path("/opt/services/scanner-web")
TEMP_FOLDER = BASE_FOLDER / "temp"
SCAN_FOLDER = BASE_FOLDER / "scans"


TEMP_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

SCAN_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)


app = Flask(__name__)


# ============================================================
# CONFIGURACIÓN DEL ESCÁNER
# ============================================================

ALLOWED_SCANNERS = {
    "brother5:bus1;dev2": "Brother DCP-T220"
}

ALLOWED_SOURCES = {
    "FlatBed": "Flatbed"
}

ALLOWED_MODES = {
    "True Gray": "True Gray",
    "24bit Color[Fast]": "Color"
}

ALLOWED_DPI = {
    "300",
    "600",
    "1200"
}

ALLOWED_FORMATS = {
    "png",
    "jpeg",
    "pdf"
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def create_filename(extension):
    """
    Crea un nombre único para un archivo definitivo.
    """
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    return (
        f"scan_{timestamp}.{extension}"
    )


def create_temp_filename(extension):
    """
    Crea un nombre para un archivo temporal.
    """
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    return (
        f".scan_{timestamp}.{extension}"
    )


def get_scan_file(filename):
    """
    Devuelve un archivo solamente si el nombre es seguro
    y el archivo realmente existe dentro de scans.
    """
    if not filename:
        return None

    safe_name = Path(filename).name

    if safe_name != filename:
        return None

    file_path = SCAN_FOLDER / safe_name

    if not file_path.is_file():
        return None

    return file_path


def get_temp_file(filename):
    """
    Devuelve un archivo temporal solamente si existe
    dentro de temp.
    """
    if not filename:
        return None

    safe_name = Path(filename).name

    if safe_name != filename:
        return None

    if not safe_name.startswith(".scan_"):
        return None

    file_path = TEMP_FOLDER / safe_name

    if not file_path.is_file():
        return None

    return file_path


def create_pdf_from_images(
    image_files,
    pdf_file
):
    """
    Crea un PDF multipágina usando img2pdf.
    """
    pdf_data = img2pdf.convert(
        image_files
    )

    with open(
        pdf_file,
        "wb"
    ) as output:

        output.write(
            pdf_data
        )


def cleanup_temp_file(filename):
    """
    Elimina un archivo temporal si existe.
    """
    file_path = get_temp_file(
        filename
    )

    if file_path is not None:
        try:
            file_path.unlink()
        except Exception:
            pass


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.route(
    "/",
    methods=["GET", "POST"]
)
def index():

    scanned = False
    error = None
    filename = None
    source_filename = None
    file_format = None
    scan_time = None


    # ========================================================
    # GET
    # ========================================================

    if request.method == "GET":

        return render_template(
            "index.html",
            scanned=False,
            error=None,
            filename=None,
            source_filename=None,
            file_format=None,
            scan_time=None
        )


    # ========================================================
    # POST - ESCANEAR
    # ========================================================

    scanner = request.form.get(
        "scanner",
        ""
    ).strip()

    source = request.form.get(
        "source",
        ""
    ).strip()

    mode = request.form.get(
        "mode",
        ""
    ).strip()

    dpi = request.form.get(
        "dpi",
        ""
    ).strip()

    file_format = request.form.get(
        "format",
        ""
    ).strip()


    # ========================================================
    # VALIDACIONES
    # ========================================================

    if scanner not in ALLOWED_SCANNERS:

        error = "Escáner no válido."

    elif source not in ALLOWED_SOURCES:

        error = "Fuente de escaneo no válida."

    elif mode not in ALLOWED_MODES:

        error = "Modo de escaneo no válido."

    elif dpi not in ALLOWED_DPI:

        error = "Resolución DPI no válida."

    elif file_format not in ALLOWED_FORMATS:

        error = "Formato de salida no válido."


    # ========================================================
    # ESCANEO
    # ========================================================

    else:

        # ----------------------------------------------------
        # Para PNG/JPEG:
        #
        # scanimage genera directamente el archivo final.
        #
        # Para PDF:
        #
        # scanimage genera primero PNG y después img2pdf
        # crea el PDF.
        # ----------------------------------------------------

        if file_format == "pdf":

            source_filename = create_temp_filename(
                "png"
            )

            source_file = (
                TEMP_FOLDER /
                source_filename
            )

            filename = create_filename(
                "pdf"
            )

            output_file = (
                SCAN_FOLDER /
                filename
            )

            scan_format = "png"

        else:

            filename = create_filename(
                file_format
            )

            source_filename = filename

            source_file = (
                SCAN_FOLDER /
                filename
            )

            output_file = source_file

            scan_format = file_format


        # ----------------------------------------------------
        # COMANDO SANE
        # ----------------------------------------------------

        command = [
            "scanimage",
            "--device-name",
            scanner,
            "--mode",
            mode,
            "--resolution",
            dpi,
            "--source",
            source,
            "--format",
            scan_format
        ]


        try:

            start_time = datetime.now()


            # ------------------------------------------------
            # EJECUTAR ESCÁNER
            # ------------------------------------------------

            with open(
                source_file,
                "wb"
            ) as output:

                result = subprocess.run(
                    command,
                    stdout=output,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=300
                )


            end_time = datetime.now()


            scan_time = round(
                (
                    end_time -
                    start_time
                ).total_seconds(),
                2
            )


            # ------------------------------------------------
            # ERROR DE SANE
            # ------------------------------------------------

            if result.returncode != 0:

                if source_file.exists():
                    source_file.unlink()

                if (
                    output_file != source_file
                    and
                    output_file.exists()
                ):
                    output_file.unlink()

                error = (
                    result.stderr.strip()
                )

                if not error:

                    error = (
                        "El escáner devolvió "
                        "un error."
                    )


            # ------------------------------------------------
            # ARCHIVO VACÍO
            # ------------------------------------------------

            elif (
                not source_file.exists()
                or
                source_file.stat().st_size == 0
            ):

                if source_file.exists():
                    source_file.unlink()

                error = (
                    "El escaneo no produjo "
                    "ningún archivo."
                )


            # ------------------------------------------------
            # PDF
            # ------------------------------------------------

            elif file_format == "pdf":

                try:

                    create_pdf_from_images(
                        [
                            str(
                                source_file
                            )
                        ],
                        output_file
                    )


                    if (
                        not output_file.exists()
                        or
                        output_file.stat().st_size == 0
                    ):

                        raise Exception(
                            "El PDF creado está vacío."
                        )


                    scanned = True


                except Exception as exc:

                    if source_file.exists():
                        source_file.unlink()

                    if output_file.exists():
                        output_file.unlink()

                    error = (
                        "No fue posible crear "
                        f"el PDF: {exc}"
                    )


            # ------------------------------------------------
            # PNG / JPEG
            # ------------------------------------------------

            else:

                scanned = True


        except subprocess.TimeoutExpired:

            if source_file.exists():
                source_file.unlink()

            if (
                output_file != source_file
                and
                output_file.exists()
            ):
                output_file.unlink()

            error = (
                "El escaneo tardó demasiado "
                "tiempo y fue cancelado."
            )


        except Exception as exc:

            if source_file.exists():
                source_file.unlink()

            if (
                output_file != source_file
                and
                output_file.exists()
            ):
                output_file.unlink()

            error = (
                f"Error interno: {exc}"
            )


    # ========================================================
    # RESPUESTA
    # ========================================================

    return render_template(
        "index.html",
        scanned=scanned,
        error=error,
        filename=filename,
        source_filename=source_filename,
        file_format=file_format,
        scan_time=scan_time
    )


# ============================================================
# HISTORIAL
#
# El servidor es ahora la fuente real del historial.
# No usamos localStorage para saber qué archivos existen.
# ============================================================

@app.route(
    "/api/history",
    methods=["GET"]
)
def api_history():

    files = []


    # --------------------------------------------------------
    # Solamente archivos definitivos.
    #
    # Los archivos .scan_ temporales quedan fuera.
    # --------------------------------------------------------

    for file_path in SCAN_FOLDER.iterdir():

        if not file_path.is_file():
            continue

        if file_path.name.startswith("."):
            continue

        extension = (
            file_path
            .suffix
            .lower()
            .replace(
                ".",
                ""
            )
        )

        if extension not in {
            "png",
            "jpg",
            "jpeg",
            "pdf"
        }:
            continue

        stat = file_path.stat()

        files.append({
            "filename":
                file_path.name,
            "format":
                extension,
            "size":
                stat.st_size,
            "modified":
                stat.st_mtime
        })


    # --------------------------------------------------------
    # Más recientes primero
    # --------------------------------------------------------

    files.sort(
        key=lambda item:
            item["modified"],
        reverse=True
    )


    return jsonify({
        "success": True,
        "files": files
    })


# ============================================================
# OBTENER ARCHIVO
# ============================================================

@app.route(
    "/file/<path:filename>"
)
def get_file(filename):

    scan_file = get_scan_file(
        filename
    )

    if scan_file is not None:

        return send_file(
            scan_file,
            as_attachment=False
        )

    return (
        "Archivo no encontrado.",
        404
    )


# ============================================================
# PREVIEW
# ============================================================

@app.route(
    "/preview/<path:filename>"
)
def preview_file(filename):

    scan_file = get_scan_file(
        filename
    )

    if scan_file is not None:

        return send_file(
            scan_file,
            as_attachment=False
        )

    return (
        "Archivo no encontrado.",
        404
    )


# ============================================================
# CREAR PDF MULTIPÁGINA
# ============================================================

@app.route(
    "/create-pdf",
    methods=["POST"]
)
def create_pdf():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "error":
                "No se recibieron datos."
        }), 400


    pages = data.get(
        "pages",
        []
    )


    if (
        not isinstance(
            pages,
            list
        )
        or
        not pages
    ):

        return jsonify({
            "error":
                "No hay páginas para crear el PDF."
        }), 400


    image_files = []


    for filename in pages:

        # ----------------------------------------------------
        # Puede ser un archivo definitivo PNG/JPEG
        # ----------------------------------------------------

        scan_file = get_scan_file(
            filename
        )


        if scan_file is not None:

            extension = (
                scan_file
                .suffix
                .lower()
            )


            if extension not in {
                ".png",
                ".jpg",
                ".jpeg"
            }:

                return jsonify({
                    "error":
                        (
                            f"El archivo {filename} "
                            "no es una imagen."
                        )
                }), 400


            image_files.append(
                str(scan_file)
            )

            continue


        # ----------------------------------------------------
        # También permitimos un temporal PNG.
        # ----------------------------------------------------

        temp_file = get_temp_file(
            filename
        )


        if temp_file is not None:

            extension = (
                temp_file
                .suffix
                .lower()
            )


            if extension not in {
                ".png",
                ".jpg",
                ".jpeg"
            }:

                return jsonify({
                    "error":
                        (
                            f"El archivo {filename} "
                            "no es una imagen."
                        )
                }), 400


            image_files.append(
                str(temp_file)
            )

            continue


        # ----------------------------------------------------
        # No existe.
        # ----------------------------------------------------

        return jsonify({
            "error":
                (
                    f"El archivo no existe: "
                    f"{filename}"
                )
        }), 404


    # ========================================================
    # CREAR PDF
    # ========================================================

    try:

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )


        pdf_filename = (
            f"documento_"
            f"{timestamp}.pdf"
        )


        pdf_file = (
            SCAN_FOLDER /
            pdf_filename
        )


        create_pdf_from_images(
            image_files,
            pdf_file
        )


        if (
            not pdf_file.exists()
            or
            pdf_file.stat().st_size == 0
        ):

            if pdf_file.exists():
                pdf_file.unlink()

            return jsonify({
                "error":
                    "El PDF creado está vacío."
            }), 500


        # ----------------------------------------------------
        # Si el PDF se creó correctamente, podemos eliminar
        # los temporales que hayan sido usados.
        # ----------------------------------------------------

        for filename in pages:

            temp_file = get_temp_file(
                filename
            )

            if temp_file is not None:

                try:
                    temp_file.unlink()
                except Exception:
                    pass


        return jsonify({
            "success":
                True,
            "filename":
                pdf_filename,
            "pages":
                len(image_files)
        })


    except Exception as exc:

        return jsonify({
            "error":
                (
                    "No fue posible crear "
                    f"el PDF: {exc}"
                )
        }), 500


# ============================================================
# ELIMINAR ARCHIVO
# ============================================================

@app.route(
    "/delete/<path:filename>",
    methods=["DELETE"]
)
def delete_file(filename):

    scan_file = get_scan_file(
        filename
    )


    if scan_file is None:

        return jsonify({
            "error":
                "El archivo no existe."
        }), 404


    try:

        scan_file.unlink()


        return jsonify({
            "success":
                True,
            "filename":
                filename
        })


    except Exception as exc:

        return jsonify({
            "error":
                str(exc)
        }), 500


# ============================================================
# LIMPIAR TEMPORALES
# ============================================================

@app.route(
    "/cleanup-temp",
    methods=["POST"]
)
def cleanup_temp():

    deleted = 0


    for file_path in TEMP_FOLDER.iterdir():

        if not file_path.is_file():
            continue

        if not file_path.name.startswith(
            ".scan_"
        ):
            continue


        try:

            file_path.unlink()
            deleted += 1

        except Exception:
            pass


    return jsonify({
        "success":
            True,
        "deleted":
            deleted
    })


# ============================================================
# INICIAR FLASK
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
