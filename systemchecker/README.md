# SystemChecker / SPV

**SystemChecker / SPV** es una herramienta en Python para visualizar, revisar y optimizar información del sistema y procesos. El paquete se instala como `spv`.

> Repositorio: `https://github.com/GrandKenzy/FerrumResources`  
> Subcarpeta del paquete: `systemchecker`  
> Nombre del paquete pip: `spv`  
> Comando principal: `spv`

---

## Requisitos

- Python 3.9 o superior.
- `pip` actualizado.
- `git` instalado.
- Windows recomendado para funciones avanzadas de administración, procesos, drivers, firewall y UAC.

Comprueba tus versiones:

```bash
python --version
python -m pip --version
git --version
```

Actualiza `pip`:

```bash
python -m pip install --upgrade pip
```

---

## Instalación desde GitHub con pip

Como `setup.py` está dentro de `systemchecker`, instala usando `#subdirectory=systemchecker`.

```bash
python -m pip install "git+https://github.com/GrandKenzy/FerrumResources.git@main#subdirectory=systemchecker"
```

En Windows PowerShell:

```powershell
python -m pip install "git+https://github.com/GrandKenzy/FerrumResources.git@main#subdirectory=systemchecker"
```

---

## Reinstalar o actualizar

```bash
python -m pip install --upgrade --force-reinstall "git+https://github.com/GrandKenzy/FerrumResources.git@main#subdirectory=systemchecker"
```

---

## Instalación local para desarrollo

```bash
git clone https://github.com/GrandKenzy/FerrumResources.git
cd FerrumResources
python -m pip install -e ./systemchecker
```

En Windows PowerShell:

```powershell
git clone https://github.com/GrandKenzy/FerrumResources.git
cd FerrumResources
python -m pip install -e .\systemchecker
```

---

## Uso básico

Ver ayuda:

```bash
spv --help
```

Ver información del paquete instalado:

```bash
python -m pip show spv
```

---

## Abrir la UI Flask

La interfaz web se abre con:

```bash
spv ui
```

Por defecto abre:

```text
http://127.0.0.1:5057
```

También existe el acceso directo alternativo:

```bash
spv-ui
```

---

## Abrir la UI en otro puerto

```bash
spv ui --port 5060
```

Luego abre:

```text
http://127.0.0.1:5060
```

---

## Abrir sin navegador automático

```bash
spv ui --no-browser
```

---

## Abrir con debug de Flask

```bash
spv ui --debug
```

---

## Abrir directamente como Administrador

En Windows, puedes pedir UAC desde la terminal:

```powershell
spv ui --admin
```

También puedes abrir normal:

```powershell
spv ui
```

Y luego usar el botón de la UI:

```text
Ejecutar como Admin
```

El elevador detecta el modo correcto de arranque:

- `spv ui`
- `spv-ui`
- `python app.py`
- `python -m app`
- instalación editable
- instalación normal con pip

Si la UI se reinicia con permisos elevados, la instancia no elevada se cierra automáticamente para liberar el puerto.

---

## Comandos CLI incluidos

```bash
spv disk --list
spv health
spv network --firewall
spv network --stats
spv os --recommend
spv programs --list
spv drivers --list
spv scanner --file RUTA_DEL_ARCHIVO
```

---

## Dependencias

El paquete instala automáticamente:

- `Flask`
- `psutil`
- `requests`

---

## Solución de problemas

### `TemplateNotFound: dashboard.html` o `TemplateNotFound: base.html`

Reinstala usando la versión que incluye `MANIFEST.in`, `templates/` y `static/`:

```bash
python -m pip install --upgrade --force-reinstall "git+https://github.com/GrandKenzy/FerrumResources.git@main#subdirectory=systemchecker"
```

El paquete debe incluir:

```text
templates/
static/
MANIFEST.in
```

### `spv` no se reconoce como comando

Verifica la instalación:

```bash
python -m pip show spv
```

En Windows, revisa que la carpeta `Scripts` de Python esté en el `PATH`.

También puedes probar:

```bash
python -m pip show -f spv
```

### Error al elevar permisos / UAC

Usa:

```powershell
spv ui --admin
```

O abre normal:

```powershell
spv ui
```

y pulsa **Ejecutar como Admin** dentro de la UI.

Si UAC se cancela, Windows devuelve acceso denegado. Si el puerto queda ocupado, cierra la terminal anterior o cambia de puerto:

```powershell
spv ui --port 5060 --admin
```

### `No module named systemchecker`

El paquete instalado se llama `spv`; `systemchecker` es la subcarpeta del repositorio, no necesariamente el nombre importable del módulo.

Correcto:

```bash
python -m pip show spv
spv ui
```

---

## Estructura esperada

```text
FerrumResources/
└── systemchecker/
    ├── setup.py
    ├── MANIFEST.in
    ├── README.md
    ├── app.py
    ├── cli.py
    ├── admin_helper.py
    ├── templates/
    ├── static/
    └── otros_archivos.py
```

El `setup.py` registra:

```text
spv=cli:main
spv-ui=app:main
```

---

## Desinstalar

```bash
python -m pip uninstall spv
```
