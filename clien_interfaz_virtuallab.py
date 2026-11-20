import os
import sys
import ast
import inspect
import zipfile
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton, QMessageBox,
    QListWidget, QTextEdit, QFileDialog, QComboBox
)
from PyQt6.QtCore import Qt

# Permitir importar virtuallab_client desde la raíz o desde client/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for ruta in (BASE_DIR, os.path.join(BASE_DIR, "client")):
    if os.path.isdir(ruta) and ruta not in sys.path:
        sys.path.append(ruta)

import virtuallab_client

URL_SERVIDOR = "http://127.0.0.1:80"
diccionario_usuarios = {}


def obtener_ruta_labs() -> str:
    """Ubica la carpeta server/labs del proyecto."""
    for base in (BASE_DIR, os.path.dirname(BASE_DIR)):
        ruta = os.path.join(base, "server", "labs")
        if os.path.isdir(ruta):
            return ruta
    return os.path.join(BASE_DIR, "server", "labs")


def obtener_labs_existentes() -> list[str]:
    """Lee los archivos .zip que ya existen en server/labs (rc.zip, voltage_divider.zip)."""
    ruta_labs = obtener_ruta_labs()
    if os.path.isdir(ruta_labs):
        return sorted(f for f in os.listdir(ruta_labs) if os.path.isfile(os.path.join(ruta_labs, f)))
    return []


def parsear_lista_servidor(respuesta) -> list[str]:
    """Decodifica bytes, listas de Python, texto separado por comas o saltos de línea."""
    if isinstance(respuesta, (bytes, bytearray)):
        respuesta = respuesta.decode("utf-8", errors="ignore")
    if isinstance(respuesta, list):
        return [str(item).strip() for item in respuesta if str(item).strip()]

    texto = str(respuesta).strip()
    if not texto or texto.lower() == "error":
        return []
    if texto.startswith("[") and texto.endswith("]"):
        try:
            return [str(item).strip() for item in ast.literal_eval(texto) if str(item).strip()]
        except Exception:
            pass
    if "," in texto and "\n" not in texto:
        return [x.strip().strip("'\"") for x in texto.split(",") if x.strip()]
    return [linea.strip() for linea in texto.splitlines() if linea.strip()]


# ==========================================
# 1. CLASES Y HERENCIA DE USUARIOS
# ==========================================
class Usuario:
    def __init__(self, user_id: str, password: str, rol_servidor: str, rol_titulo: str, nombre: str = ""):
        self.nombre = nombre.strip()
        self.user_id = user_id.strip()
        self.password = password.strip()
        self.rol_servidor = rol_servidor
        self.rol_titulo = rol_titulo

    def registrar(self):
        if not all((self.nombre, self.user_id, self.password)):
            return False, "Completa nombre, ID y contraseña."
        try:
            res = str(virtuallab_client.registerUser(
                URL_SERVIDOR, self.nombre, self.user_id, self.rol_servidor, self.password
            ))
            if "registered" in res.lower() and "already" not in res.lower():
                diccionario_usuarios[self.user_id] = {
                    "nombre": self.nombre,
                    "rol": self.rol_servidor,
                    "password": self.password
                }
                return True, res
            return False, f"No se pudo registrar: {res}"
        except Exception as e:
            return False, f"Error de conexión: {e}"

    def iniciar_sesion(self):
        if not self.user_id or not self.password:
            return False, "Ingresa usuario (ID) y contraseña."
        try:
            res = str(virtuallab_client.openSession(URL_SERVIDOR, self.user_id, self.password))
            if "succesfully opened" not in res.lower():
                return False, "Credenciales incorrectas o usuario no registrado."

            if not self.validar_rol():
                self.cerrar_sesion()
                return False, f"Este ID no corresponde al rol de {self.rol_titulo}."

            return True, res
        except Exception as e:
            return False, f"Error de conexión: {e}"

    def validar_rol(self) -> bool:
        return True

    def cerrar_sesion(self):
        try:
            virtuallab_client.closeSession(URL_SERVIDOR, self.user_id)
        except Exception:
            pass


class Estudiante(Usuario):
    def __init__(self, user_id: str, password: str, nombre: str = ""):
        super().__init__(user_id, password, "student", "Estudiante", nombre)

    def validar_rol(self) -> bool:
        res = virtuallab_client.listStudentLabs(URL_SERVIDOR, self.user_id)
        if isinstance(res, (bytes, bytearray)):
            res = res.decode("utf-8", errors="ignore")
        return str(res).strip() != "error"

    def obtener_laboratorios(self) -> list[str]:
        """Obtiene los laboratorios asignados y muestra también los existentes en el servidor."""
        asignados = []
        try:
            res = virtuallab_client.listStudentLabs(URL_SERVIDOR, self.user_id)
            asignados = parsear_lista_servidor(res)
        except Exception:
            pass

        # Si aún no tiene asignados en assignments.txt, mostrar los que ya existen en server/labs
        if asignados:
            return asignados
        return obtener_labs_existentes()

    def descargar_y_visualizar(self, nombre_lab: str) -> tuple[bool, str]:
        """Descarga el .zip del servidor (o lo toma de server/labs), lo extrae y muestra su contenido."""
        nombre_zip = nombre_lab if nombre_lab.endswith(".zip") else f"{nombre_lab}.zip"
        carpeta_descargas = os.path.join(BASE_DIR, f"descargas_{self.user_id}")
        os.makedirs(carpeta_descargas, exist_ok=True)
        ruta_zip = os.path.join(carpeta_descargas, nombre_zip)

        try:
            params = inspect.signature(virtuallab_client.downloadLab).parameters
            if len(params) >= 4:
                res = virtuallab_client.downloadLab(URL_SERVIDOR, self.user_id, nombre_zip, ruta_zip)
            else:
                res = virtuallab_client.downloadLab(URL_SERVIDOR, self.user_id, nombre_zip)

            if isinstance(res, (bytes, bytearray)) and res != b"error":
                with open(ruta_zip, "wb") as f:
                    f.write(res)
            elif not os.path.exists(ruta_zip):
                # Respaldo si aún no estaba asignado formalmente en assignments.txt
                ruta_servidor = os.path.join(obtener_ruta_labs(), nombre_zip)
                if os.path.isfile(ruta_servidor):
                    with open(ruta_servidor, "rb") as src, open(ruta_zip, "wb") as dst:
                        dst.write(src.read())
                else:
                    return False, "No se encontró el archivo del laboratorio."

            carpeta_extraida = os.path.join(carpeta_descargas, nombre_zip.replace(".zip", ""))
            os.makedirs(carpeta_extraida, exist_ok=True)

            detalle = [f"Laboratorio: {nombre_zip}", f"Guardado en: {ruta_zip}\n"]
            if zipfile.is_zipfile(ruta_zip):
                with zipfile.ZipFile(ruta_zip, "r") as zf:
                    zf.extractall(carpeta_extraida)
                    detalle.append("Archivos dentro del laboratorio:")
                    for arch in zf.namelist():
                        detalle.append(f"  • {arch}")
                        if arch.lower().endswith((".txt", ".md", ".py", ".csv", ".json")):
                            contenido = zf.read(arch).decode("utf-8", errors="ignore")
                            detalle.append(f"\n--- Contenido de {arch} ---\n{contenido[:1000]}")
            else:
                with open(ruta_zip, "r", encoding="utf-8", errors="ignore") as f:
                    detalle.append(f"Contenido:\n{f.read()[:1000]}")

            return True, "\n".join(detalle)
        except Exception as e:
            return False, f"Error al visualizar laboratorio: {e}"


class Maestro(Usuario):
    def __init__(self, user_id: str, password: str, nombre: str = ""):
        super().__init__(user_id, password, "professor", "Maestro", nombre)

    def validar_rol(self) -> bool:
        res = virtuallab_client.listProfessorsLabs(URL_SERVIDOR, self.user_id)
        if isinstance(res, (bytes, bytearray)):
            res = res.decode("utf-8", errors="ignore")
        return str(res).strip() != "error"

    def obtener_laboratorios_subidos(self) -> list[str]:
        """Lista los laboratorios del servidor (rc.zip, voltage_divider.zip y nuevos)."""
        labs_srv = []
        try:
            res = virtuallab_client.listProfessorsLabs(URL_SERVIDOR, self.user_id)
            labs_srv = parsear_lista_servidor(res)
        except Exception:
            pass

        # Combinar con los existentes en server/labs para garantizar que siempre aparezcan
        combinados = sorted(set(labs_srv + obtener_labs_existentes()))
        return combinados

    def obtener_estudiantes(self) -> list[str]:
        """Obtiene los IDs de estudiantes registrados."""
        try:
            res = virtuallab_client.listStudents(URL_SERVIDOR, self.user_id)
            return parsear_lista_servidor(res)
        except Exception:
            return []

    def cargar_laboratorio(self, ruta_archivo: str) -> tuple[bool, str]:
        if not ruta_archivo or not os.path.isfile(ruta_archivo):
            return False, "Selecciona un archivo válido."
        try:
            params = inspect.signature(virtuallab_client.uploadLab).parameters
            if len(params) >= 4:
                with open(ruta_archivo, "rb") as f:
                    res = virtuallab_client.uploadLab(
                        URL_SERVIDOR, self.user_id, os.path.basename(ruta_archivo), f.read()
                    )
            else:
                res = virtuallab_client.uploadLab(URL_SERVIDOR, self.user_id, ruta_archivo)

            res_str = res.decode("utf-8", errors="ignore") if isinstance(res, bytes) else str(res)
            if "succesfully received" in res_str.lower() or "ok" in res_str.lower():
                return True, f"Laboratorio '{os.path.basename(ruta_archivo)}' cargado correctamente."
            return False, f"Respuesta del servidor: {res_str}"
        except Exception as e:
            return False, f"Error al subir laboratorio: {e}"

    def asignar_laboratorio(self, lab_name: str, student_id: str) -> tuple[bool, str]:
        if not lab_name or not student_id:
            return False, "Selecciona un laboratorio y un estudiante."
        try:
            res = virtuallab_client.assignLab(URL_SERVIDOR, self.user_id, lab_name, student_id)
            res_str = res.decode("utf-8", errors="ignore") if isinstance(res, bytes) else str(res)
            if "succesfully assigned" in res_str.lower():
                return True, f"Laboratorio '{lab_name}' asignado al estudiante {student_id}."
            return False, f"No se pudo asignar: {res_str}"
        except Exception as e:
            return False, f"Error al asignar: {e}"


# ==========================================
# 2. CLASES Y HERENCIA DE VISTAS (PyQt6)
# ==========================================
class VistaBase(QWidget):
    def __init__(self, ventana):
        super().__init__()
        self.ventana = ventana
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(22, 18, 22, 18)
        self.layout.setSpacing(10)


class VistaLogin(VistaBase):
    def __init__(self, ventana):
        super().__init__(ventana)

        titulo = QLabel("Laboratorio Virtual")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(titulo)

        fila_rol = QHBoxLayout()
        self.rb_estudiante = QRadioButton("Estudiante")
        self.rb_maestro = QRadioButton("Maestro")
        self.rb_estudiante.setChecked(True)
        fila_rol.addWidget(self.rb_estudiante)
        fila_rol.addWidget(self.rb_maestro)
        self.layout.addLayout(fila_rol)

        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("ID de usuario (Ej: 99999 o 787878)")
        self.layout.addWidget(self.txt_usuario)

        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("Contraseña")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.returnPressed.connect(self.entrar)
        self.layout.addWidget(self.txt_password)

        btn_entrar = QPushButton("Ingresar")
        btn_entrar.clicked.connect(self.entrar)
        self.layout.addWidget(btn_entrar)

        btn_registro = QPushButton("Registrar Nuevo Usuario")
        btn_registro.clicked.connect(self.ventana.mostrar_registro)
        self.layout.addWidget(btn_registro)

    def entrar(self):
        uid = self.txt_usuario.text()
        pwd = self.txt_password.text()
        usuario = Estudiante(uid, pwd) if self.rb_estudiante.isChecked() else Maestro(uid, pwd)

        ok, msg = usuario.iniciar_sesion()
        if ok:
            self.ventana.cambiar_vista(usuario)
        else:
            QMessageBox.warning(self, "Acceso Denegado", msg)


class VistaRegistro(VistaBase):
    def __init__(self, ventana):
        super().__init__(ventana)

        titulo = QLabel("Registrar Usuario")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(titulo)

        fila_rol = QHBoxLayout()
        self.rb_estudiante = QRadioButton("Estudiante")
        self.rb_maestro = QRadioButton("Maestro")
        self.rb_estudiante.setChecked(True)
        fila_rol.addWidget(self.rb_estudiante)
        fila_rol.addWidget(self.rb_maestro)
        self.layout.addLayout(fila_rol)

        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre completo (Ej: Carlos)")
        self.layout.addWidget(self.txt_nombre)

        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("ID único (Ej: 202)")
        self.layout.addWidget(self.txt_usuario)

        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("Contraseña")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.txt_password)

        btn_guardar = QPushButton("Guardar Usuario")
        btn_guardar.clicked.connect(self.guardar)
        self.layout.addWidget(btn_guardar)

        btn_volver = QPushButton("Volver al Login")
        btn_volver.clicked.connect(self.ventana.mostrar_login)
        self.layout.addWidget(btn_volver)

    def guardar(self):
        nombre = self.txt_nombre.text()
        uid = self.txt_usuario.text()
        pwd = self.txt_password.text()
        nuevo = Estudiante(uid, pwd, nombre) if self.rb_estudiante.isChecked() else Maestro(uid, pwd, nombre)

        ok, msg = nuevo.registrar()
        if ok:
            QMessageBox.information(self, "Registro Exitoso", msg)
            self.ventana.mostrar_login()
        else:
            QMessageBox.warning(self, "Error", msg)


class VistaEstudiante(VistaBase):
    def __init__(self, ventana, estudiante: Estudiante):
        super().__init__(ventana)
        self.usuario = estudiante

        titulo = QLabel(f"Panel Estudiante (ID: {estudiante.user_id})")
        titulo.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.layout.addWidget(titulo)

        self.layout.addWidget(QLabel("Laboratorios disponibles / asignados:"))
        self.lista_labs = QListWidget()
        self.layout.addWidget(self.lista_labs)

        fila_botones = QHBoxLayout()
        btn_actualizar = QPushButton("Actualizar Lista")
        btn_actualizar.clicked.connect(self.cargar_lista)
        fila_botones.addWidget(btn_actualizar)

        btn_ver = QPushButton("Descargar y Visualizar")
        btn_ver.clicked.connect(self.visualizar_lab)
        fila_botones.addWidget(btn_ver)
        self.layout.addLayout(fila_botones)

        self.layout.addWidget(QLabel("Vista previa del laboratorio:"))
        self.visor_contenido = QTextEdit()
        self.visor_contenido.setReadOnly(True)
        self.visor_contenido.setPlaceholderText("Selecciona un laboratorio y presiona 'Descargar y Visualizar'...")
        self.layout.addWidget(self.visor_contenido)

        btn_salir = QPushButton("Cerrar Sesión")
        btn_salir.clicked.connect(self.salir)
        self.layout.addWidget(btn_salir)

        self.cargar_lista()

    def cargar_lista(self):
        self.lista_labs.clear()
        labs = self.usuario.obtener_laboratorios()
        self.lista_labs.addItems(labs)
        if labs:
            self.lista_labs.setCurrentRow(0)

    def visualizar_lab(self):
        item = self.lista_labs.currentItem()
        if not item:
            QMessageBox.warning(self, "Atención", "Selecciona un laboratorio de la lista.")
            return

        ok, info = self.usuario.descargar_y_visualizar(item.text())
        if ok:
            self.visor_contenido.setPlainText(info)
        else:
            QMessageBox.warning(self, "Error", info)

    def salir(self):
        self.usuario.cerrar_sesion()
        self.ventana.mostrar_login()


class VistaMaestro(VistaBase):
    def __init__(self, ventana, maestro: Maestro):
        super().__init__(ventana)
        self.usuario = maestro

        titulo = QLabel(f"Panel Maestro (ID: {maestro.user_id})")
        titulo.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.layout.addWidget(titulo)

        btn_subir = QPushButton("Cargar Nuevo Laboratorio (.zip)")
        btn_subir.clicked.connect(self.subir_archivo)
        self.layout.addWidget(btn_subir)

        self.layout.addWidget(QLabel("Laboratorios existentes en el servidor:"))
        self.lista_labs = QListWidget()
        self.layout.addWidget(self.lista_labs)

        # Sección para asignar el laboratorio seleccionado a un estudiante
        self.layout.addWidget(QLabel("Asignar laboratorio seleccionado a estudiante:"))
        fila_asignar = QHBoxLayout()
        self.combo_estudiantes = QComboBox()
        fila_asignar.addWidget(self.combo_estudiantes)

        btn_asignar = QPushButton("Asignar")
        btn_asignar.clicked.connect(self.asignar_a_estudiante)
        fila_asignar.addWidget(btn_asignar)
        self.layout.addLayout(fila_asignar)

        btn_salir = QPushButton("Cerrar Sesión")
        btn_salir.clicked.connect(self.salir)
        self.layout.addWidget(btn_salir)

        self.actualizar_datos()

    def actualizar_datos(self):
        self.lista_labs.clear()
        labs = self.usuario.obtener_laboratorios_subidos()
        self.lista_labs.addItems(labs)
        if labs:
            self.lista_labs.setCurrentRow(0)

        self.combo_estudiantes.clear()
        self.combo_estudiantes.addItems(self.usuario.obtener_estudiantes())

    def subir_archivo(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de laboratorio", "", "Archivos ZIP (*.zip);;Todos los archivos (*.*)"
        )
        if not ruta:
            return

        ok, msg = self.usuario.cargar_laboratorio(ruta)
        if ok:
            QMessageBox.information(self, "Carga Exitosa", msg)
            self.actualizar_datos()
        else:
            QMessageBox.warning(self, "Error al Subir", msg)

    def asignar_a_estudiante(self):
        item = self.lista_labs.currentItem()
        estudiante_id = self.combo_estudiantes.currentText()
        if not item or not estudiante_id:
            QMessageBox.warning(self, "Atención", "Selecciona un laboratorio y un estudiante.")
            return

        ok, msg = self.usuario.asignar_laboratorio(item.text(), estudiante_id)
        if ok:
            QMessageBox.information(self, "Asignación Exitosa", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def salir(self):
        self.usuario.cerrar_sesion()
        self.ventana.mostrar_login()


# ==========================================
# 3. VENTANA PRINCIPAL
# ==========================================
class AppVirtualLab(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VirtualLab")
        self.resize(450, 460)
        self.mostrar_login()

    def mostrar_login(self):
        self.setCentralWidget(VistaLogin(self))

    def mostrar_registro(self):
        self.setCentralWidget(VistaRegistro(self))

    def cambiar_vista(self, usuario: Usuario):
        if isinstance(usuario, Estudiante):
            self.setCentralWidget(VistaEstudiante(self, usuario))
        else:
            self.setCentralWidget(VistaMaestro(self, usuario))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = AppVirtualLab()
    ventana.show()
    sys.exit(app.exec())