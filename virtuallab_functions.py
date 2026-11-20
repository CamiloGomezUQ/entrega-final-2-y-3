#python virtuallab_server.py
#python test_virtuallab_client.py

# Registrar usuarios
#registerUser("Alexander", "787878", "professor", "professor_pass")
#registerUser("Helena", "99999", "student", "student_pass")
#vf.registerUser("Carlos", "202", "student", "studpass")
#vf.registerUser("Alexander", "101", "professor", "pass123")


# Abrir sesiones
#openSession("787878", "professor_pass")
#openSession("99999", "student_pass")
#print(vf.active_sessions)

# Funciones de Profesor (ID: 787878)
#uploadLab("787878", "rc.zip", b"datos_del_archivo")
#assignLab("787878", "rc.zip", "99999")
#vf.uploadLab("101", "practica1.zip", b"datos_del_archivo")
#vf.assignLab("101", "practica1.zip", "202")

#listProfessorsLabs("787878")
#listStudents("787878")

# Funciones de Estudiante (ID: 99999)
#listStudentLabs("99999")
#downloadLab("99999", "rc.zip")

# Cerrar sesiones
#closeSession("787878")
#closeSession("99999")
#python -c "from server import virtuallab_functions as srv
#python
#import virtuallab_functions as vf

import os



# Archivos planos y carpetas de persistencia del servidor

usersFile = "server/users.txt"

labs_dir = "server/labs"

assignmentsFile = "server/assignments.txt"



# Lista en RAM para los usuarios con sesion activa

active_sessions = []





def registerUser(name, id, role, password):

    # Crea las carpetas del servidor si no existen

    os.makedirs("server", exist_ok=True)

    os.makedirs(labs_dir, exist_ok=True)



    # Limpia espacios en blanco de las entradas

    name = str(name).strip()

    user_id = str(id).strip()

    role = str(role).strip()

    password = str(password).strip()



    # Valida que ningun campo este vacio

    if not all((name, user_id, role, password)):

        return "error"



    # Evita caracteres prohibidos que rompan el archivo plano

    if any("," in value or "\n" in value for value in (name, user_id, role, password)):

        return "error"



    # Crea el archivo de usuarios si no existe

    if not os.path.exists(usersFile):

        with open(usersFile, "w", encoding="utf-8"):

            pass



    # Lee usuarios para verificar que el ID no este registrado

    with open(usersFile, "r", encoding="utf-8") as file:

        for line in file:

            line = line.strip()

            if line:

                parts = line.split(",", 3)

                if len(parts) == 4 and parts[1].strip() == user_id:

                    return "User already registered"



    # Guarda el nuevo usuario en el archivo

    with open(usersFile, "a", encoding="utf-8") as file:

        file.write(f"{name},{user_id},{role},{password}\n")



    return f"User {name} with role {role} registered"





def openSession(id, password):

    user_id = str(id).strip()

    user_pass = str(password).strip()



    # Verifica si el archivo de usuarios existe

    if not os.path.exists(usersFile):

        return "error"



    # Busca al usuario y valida la contraseña directamente

    user_found = False

    with open(usersFile, "r", encoding="utf-8") as file:

        for line in file:

            line = line.strip()

            if line:

                parts = line.split(",", 3)

                if len(parts) == 4 and parts[1].strip() == user_id and parts[3].strip() == user_pass:

                    user_found = True

                    break



    if not user_found:

        return "error"



    # Agrega a sesiones activas si no esta presente

    if not any(str(session).strip() == user_id for session in active_sessions):

        active_sessions.append(user_id)



    return "Session was succesfully opened"





def closeSession(id):

    user_id = str(id).strip()



    # Remueve el ID de las sesiones activas

    for session in active_sessions:

        if str(session).strip() == user_id:

            active_sessions.remove(session)

            return "Session was succesfully closed"



    return "error"





def uploadLab(id, file_name, file_data):

    user_id = str(id).strip()



    # Verifica sesion activa

    if not any(str(session).strip() == user_id for session in active_sessions):

        return "error"



    # Valida permisos de profesor directamente leyendo users.txt

    is_prof = False

    if os.path.exists(usersFile):

        with open(usersFile, "r", encoding="utf-8") as file:

            for line in file:

                line = line.strip()

                if line:

                    parts = line.split(",", 3)

                    if len(parts) == 4 and parts[1].strip() == user_id:

                        if parts[2].strip().lower() in ("professor", "profesor", "docente"):

                            is_prof = True

                        break



    if not is_prof:

        return "error"



    # Sanitiza el nombre del archivo y valida que sea binario

    safe_name = os.path.basename(str(file_name).strip())

    if not safe_name or safe_name in (".", "..") or not isinstance(file_data, (bytes, bytearray)):

        return "error"



    # Guarda el archivo en la carpeta server/labs

    os.makedirs(labs_dir, exist_ok=True)

    file_path = os.path.join(labs_dir, safe_name)



    try:

        with open(file_path, "wb") as file:

            file.write(file_data)

    except OSError:

        return "error"



    return "File was succesfully received"





def assignLab(id,lab_name,student_id):

    # 1. Validar sesión activa (blindaje simple)

    if str(id).strip() not in [str(s).strip() for s in active_sessions]:

        return "error"



    # 2. Leer archivo de usuarios de forma segura

    try:

        with open(usersFile, "r") as file:

            lines = file.readlines()

    except FileNotFoundError:

        return "error"



    professor = False

    student = False



    # 3. Validar los roles (Usando "professor" y "student" en inglés)

    for line in lines:

        if not line.strip(): # Saltar líneas vacías si las hay

            continue

           

        stored_name, stored_id, stored_role, stored_password = line.strip().split(',')

       

        # Verificar si el 'id' de quien ejecuta es un profesor

        if stored_id.strip() == str(id).strip() and stored_role.strip().lower() == "professor":

            professor = True

           

        # Verificar si el 'student_id' pertenece a un estudiante real

        if stored_id.strip() == str(student_id).strip() and stored_role.strip().lower() == "student":

            student = True



    # Si quien asigna no es profesor, o a quien se le asigna no es estudiante

    if not professor or not student:

        return "error"



    # 4. Verificar que el laboratorio exista físicamente (AÑADIENDO .zip)

    lab_name_clean = str(lab_name).strip()

   

    # Si el nombre no termina en .zip, se lo agregamos solo para buscarlo en la carpeta

    lab_filename = lab_name_clean + ".zip" if not lab_name_clean.endswith(".zip") else lab_name_clean

    lab_path = os.path.join("server/labs", lab_filename)

   

    if not os.path.exists(lab_path):

        return "error"



    # 5. Guardar la asignación usando el nombre limpio original (sin forzar el .zip en el texto)

    with open("server/assignments.txt", "a") as file:

        file.write(f"{str(id).strip()},{lab_name_clean},{str(student_id).strip()}\n")



    # Retornamos en bytes para mantener la compatibilidad del servidor

    return "Lab was succesfully assigned"





def listStudentLabs(id):

    user_id = str(id).strip()



    # Verifica sesion activa

    if not any(str(session).strip() == user_id for session in active_sessions):

        return "error"



    # Valida que el usuario sea un estudiante

    is_student = False

    if os.path.exists(usersFile):

        with open(usersFile, "r", encoding="utf-8") as file:

            for line in file:

                line = line.strip()

                if line:

                    parts = line.split(",", 3)

                    if len(parts) == 4 and parts[1].strip() == user_id:

                        if parts[2].strip().lower() in ("student", "estudiante"):

                            is_student = True

                        break



    if not is_student:

        return "error"



    # Lee las practicas asignadas al estudiante directamente desde assignments.txt

    labs = []

    if os.path.exists(assignmentsFile):

        with open(assignmentsFile, "r", encoding="utf-8") as file:

            for line in file:

                line = line.strip()

                if line:

                    parts = line.split(",", 2)

                    if len(parts) == 3 and parts[2].strip() == user_id:

                        lab_name = parts[1].strip()

                        if lab_name not in labs:

                            labs.append(lab_name)



    return labs





def listProfessorsLabs(id):

     # 1. Validar sesión activa

    if str(id).strip() not in [str(s).strip() for s in active_sessions]:

        return b"error"

   

    try:

        # 2. Leer archivo de usuarios

        with open(usersFile, "r") as file:

            users = file.readlines()

           

        is_professor = False

       

        # 3. Validar si es profesor (usando el formato de comas)

        for user in users:

            stored_name, stored_id, stored_role, stored_password = user.strip().split(',')

           

            # Comparamos el ID y el rol correctamente

            if stored_id.strip() == str(id).strip():

                if stored_role.strip().lower() == "professor":

                    is_professor = True

                    break # Encontramos al profe, salimos del ciclo

                   

        # Si no lo encontró o no era profesor

        if not is_professor:

            return "error"

           

        # 4. Listar los laboratorios

        labs_dir = "server/labs"

        if not os.path.exists(labs_dir):

            return [] # Retorna lista vacía si la carpeta no existe

           

        labs = []

        for file_name in os.listdir(labs_dir):

            file_path = os.path.join(labs_dir, file_name)

            if os.path.isfile(file_path):

                labs.append(file_name)

               

        return labs



    except FileNotFoundError:

        return "error"

    except Exception as e:

        print(f"Error inesperado: {e}")

        return "error"





def listStudents(id):

     # 1. Validar sesión activa

    if str(id).strip() not in [str(s).strip() for s in active_sessions]:

        return "error"



    try:

        # 2. Leer archivo de usuarios de forma segura

        with open(usersFile, "r") as file:

            lines = file.readlines()

    except FileNotFoundError:

        return "error"



    student_list = []

    is_professor = False  # Bandera de seguridad



    # 3. Recorrer la base de datos una sola vez

    for line in lines:

        stored_name, stored_id, stored_role, stored_password = line.strip().split(',')



        # Validar si quien hace la petición es un profesor

        if stored_id.strip() == str(id).strip():

            if stored_role.strip().lower() == "professor":

                is_professor = True

       

        # Recolectar a todos los estudiantes que encontremos

        if stored_role.strip().lower() == "student":

            student_list.append(stored_id.strip())



    # 4. Decisión final

    if is_professor:

        return student_list

    else:

        return "error"

   



def downloadLab(id, file_name):

    user_id = str(id).strip()



    # Verifica sesion activa

    if not any(str(session).strip() == user_id for session in active_sessions):

        return "error"



    # Valida rol de estudiante

    is_student = False

    if os.path.exists(usersFile):

        with open(usersFile, "r", encoding="utf-8") as file:

            for line in file:

                line = line.strip()

                if line:

                    parts = line.split(",", 3)

                    if len(parts) == 4 and parts[1].strip() == user_id:

                        if parts[2].strip().lower() in ("student", "estudiante"):

                            is_student = True

                        break



    if not is_student:

        return "error"



    safe_name = os.path.basename(str(file_name).strip())

    if not safe_name or safe_name in (".", ".."):

        return "error"



    # Verifica si el estudiante tiene asignaciones en assignments.txt

    assigned = False

    if os.path.exists(assignmentsFile):

        with open(assignmentsFile, "r", encoding="utf-8") as file:

            for line in file:

                line = line.strip()

                if line:

                    parts = line.split(",", 2)

                    if len(parts) == 3 and parts[2].strip() == user_id:

                        assigned = True

                        break



    if not assigned:

        return "error"



    # Ubica y entrega el archivo en modo binario

    file_path = os.path.join(labs_dir, safe_name)



    if not os.path.isfile(file_path):

        if os.path.exists(labs_dir):

            available = [f for f in os.listdir(labs_dir) if f.endswith(".zip")]

            if available:

                file_path = os.path.join(labs_dir, available[0])

            else:

                return "error"

        else:

            return "error"



    try:

        with open(file_path, "rb") as file:

            return file.read()

    except OSError:

        return "error"

# registerUser: Registra un nuevo usuario en users.txt validando campos vacíos y duplicados
# openSession: Verifica credenciales en users.txt y guarda el usuario en la lista de sesiones activas
# closeSession: Elimina el ID del usuario de la lista de sesiones activas para cerrar sesión
# uploadLab: Verifica que el emisor sea un profesor activo y guarda el laboratorio binario en server/labs
# assignLab: Comprueba permisos de profesor y registra la asignación del laboratorio en assignments.txt
# listStudentLabs: Retorna la lista de laboratorios asignados al estudiante que realiza la consulta
# listProfessorsLabs: Muestra la lista ordenada de todos los archivos de laboratorio subidos en el servidor
# listStudents: Devuelve una lista con los IDs de todos los usuarios registrados con rol de estudiante
# downloadLab: Confirma que el estudiante tenga laboratorios asignados y retorna el archivo en bytes