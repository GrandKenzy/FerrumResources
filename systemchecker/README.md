# SPV 3.0 — System Process Viewer & Optimizer

SPV 3.0 es una plataforma avanzada de gestión de sistemas diseñada para monitoreo, limpieza, seguridad y mantenimiento preventivo. Ofrece tanto una interfaz web moderna (Flask) como una potente interfaz de línea de comandos (CLI).

## 🚀 Características Principales

- **📊 Dashboard en Tiempo Real**: Visualización de CPU, RAM, Disco y Procesos críticos con una estética premium.
- **🧹 Limpieza Segura de Disco**: Algoritmo que identifica archivos basura (`.tmp`, `.log`, cache) sin tocar documentos personales.
- **🏥 Salud del PC**: Ejecución automatizada de SFC, DISM, reset de Winsock y limpieza de registros de eventos.
- **🔥 Control de Firewall**: Gestión de perfiles (Dominio/Privado/Público) y bloqueo/desbloqueo de IPs en tiempo real.
- **🔑 Activación de Windows**: Soporte para claves GVLK oficiales de Microsoft con auto-detección de edición.
- **⛓️ Cola de Tareas (Jobs)**: Ejecución asíncrona (Threading) para no bloquear la interfaz durante tareas pesadas.
- **💻 CLI Integrada**: Acceso a todas las herramientas directamente desde la terminal.

---

## 🛠️ Instalación y Uso

### 1. Requisitos
- Python 3.10+
- Privilegios de Administrador (para acciones de sistema como Firewall/Disco).

### 2. Configuración
Instala las dependencias necesarias:
```bash
pip install -r requirements.txt
```

### 3. Ejecución de la Web UI
```bash
python app.py
```
Accede a `http://127.0.0.1:5057`.

### 4. Uso de la CLI
```bash
python cli.py --help
python cli.py disk --list
python cli.py health
python cli.py network --firewall
```

---

## 🔒 Seguridad (Modo de Poder)

Por defecto, las acciones que modifican el sistema están protegidas. Puedes activarlas de dos formas:
1. **Variable de Entorno**: Configura `ENABLE_POWER_ACTIONS=true` antes de iniciar la app.
2. **Ajustes en UI**: Ve a la pestaña **Settings** y activa el **Modo de Poder**.

---

## 🤖 Información para IAs (Contexto de Desarrollo)

Si eres un agente de IA trabajando en este proyecto, aquí tienes la estructura clave:

- `app.py`: Punto de entrada Flask y definición de rutas API.
- `cli.py`: Interfaz de comandos para terminal.
- `disk_manager.py`: Lógica de limpieza segura, particionado y BitLocker.
- `pc_health.py`: Diagnóstico y reparación del sistema (SFC/DISM).
- `firewall_manager.py`: Abstracción de `netsh` para control de red.
- `security.py`: Capa de seguridad, CSRF y validación de permisos de "poder".
- `static/css/styles.css`: Sistema de diseño moderno con soporte nativo de modo oscuro.
- `static/js/core.js`: Motor de comunicación asíncrona y sistema de notificaciones (Toasts).

**Seguridad de Limpieza**: La función `safe_clean_disk` en `disk_manager.py` utiliza listas blancas de extensiones basura. No realiza un `format` ni borrado recursivo total en particiones de usuario.

---

## 📄 Licencia
Este proyecto está diseñado para uso administrativo y educativo. El uso de herramientas de activación GVLK cumple con la documentación pública de Microsoft para entornos de prueba.
