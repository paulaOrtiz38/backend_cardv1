# cards_v1
Si cambias el nombre de la carpeta o descargas un nuevo proyecto en otra maquina las rutas dejan de existir.
👉 Por eso en Python es más rápido borrar venv y crearlo otra vez que intentar repararlo.

1. NO SUBIR NUNCA LA CARPETA VENV A GIT USA MEJOR QUE CREA UN ARCHIVO REQUIREMENTS.TXT CON LA LISTA DE LIBRERIAS INSTALADAS EN EL PROYECTO
   pip freeze > requirements.txt
2. si cambias de nombre o de máquina solo haces AQUI "Instala exactamente lo que está escrito en EL archivo requirements.txt"
   pip install -r requirements.txt

para inicializar el proyecto se debe tener habilitado el venc, Si no aparece (venv) en la consola, significa que el entorno virtual no está activado (aunque sí puede estar creado).
1. crearlo de nuevo 
   python -m venv venv
2. activarlo
   venv\Scripts\activate

Luego se debe instalar Django
1. pip install django
9