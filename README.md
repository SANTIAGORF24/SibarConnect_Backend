# SibarConnect Backend

## Descripción General

Backend de la aplicación SibarConnect desarrollado en FastAPI con Python. Proporciona APIs para gestión de chats, usuarios, empresas y análisis de inteligencia artificial.

## Estructura del Proyecto

### 📁 Directorios Principales

#### `/app/` - Aplicación principal

- **`/api/`** - Endpoints de la API REST
- **`/core/`** - Configuración y utilidades centrales
- **`/db/`** - Configuración de base de datos
- **`/models/`** - Modelos de SQLAlchemy
- **`/schemas/`** - Esquemas Pydantic para validación
- **`/services/`** - Lógica de negocio

#### `/data/` - Base de datos SQLite

- **`app.db`** - Base de datos principal

#### `/media/` - Archivos multimedia

- **`/company_1/`** - Archivos por empresa
  - **`/uploads/`** - Archivos subidos por usuarios
  - **`/whatsapp/`** - Archivos de WhatsApp
  - **`/stickers/`** - Stickers personalizados
  - **`/templates/`** - Plantillas de mensajes

#### `/scripts/` - Scripts de utilidad

- **`create_admin.py`** - Crear usuario administrador
- **`create_stickers_table.py`** - Migración de tabla de stickers
- **`migrate_add_attachment_url.py`** - Migración de URLs de adjuntos
- **`migrate_ycloud.py`** - Migración de YCloud

## 🚀 API Endpoints

### 🔐 Autenticación (`/api/auth/`)

- **`POST /login`** - Inicio de sesión de usuarios

### 💬 Chats (`/api/chats/`)

- **`GET /`** - Obtener chats de una empresa con filtros
- **`GET /{chat_id}`** - Obtener chat específico
- **`POST /bulk`** - Actualización masiva de chats
- **`POST /assign`** - Asignar chat a usuario
- **`POST /status`** - Actualizar estado del chat
- **`POST /pin`** - Fijar chat
- **`POST /unpin`** - Desfijar chat
- **`POST /snooze`** - Pausar chat
- **`POST /unsnooze`** - Reanudar chat

### 🤖 Inteligencia Artificial (`/api/chats/ai/`)

- **`POST /insights`** - Generar insights del chat usando Gemini AI
- **`GET /insights`** - Obtener insights existentes
- **`POST /summaries/generate`** - Generar resumen del chat
- **`GET /summaries/{chat_id}`** - Obtener resumen del chat
- **`POST /assist-draft`** - Asistir en la redacción de mensajes

### 📱 Mensajes (`/api/chats/messages/`)

- **`GET /{chat_id}`** - Obtener mensajes de un chat
- **`POST /{chat_id}`** - Enviar mensaje
- **`POST /{chat_id}/bulk`** - Enviar múltiples mensajes

### 🏢 Empresas (`/api/companies/`)

- **`GET /`** - Obtener información de la empresa
- **`POST /stickers`** - Subir sticker personalizado
- **`GET /stickers`** - Obtener stickers de la empresa

### 👥 Usuarios (`/api/users/`)

- **`GET /`** - Obtener usuarios de la empresa
- **`POST /`** - Crear nuevo usuario
- **`GET /{user_id}`** - Obtener usuario específico
- **`PUT /{user_id}`** - Actualizar usuario
- **`DELETE /{user_id}`** - Eliminar usuario

### 🔑 Roles (`/api/roles/`)

- **`GET /`** - Obtener roles disponibles
- **`POST /`** - Crear nuevo rol
- **`PUT /{role_id}`** - Actualizar rol
- **`DELETE /{role_id}`** - Eliminar rol

### 📋 Plantillas (`/api/templates/`)

- **`GET /`** - Obtener plantillas de mensajes
- **`POST /`** - Crear nueva plantilla
- **`PUT /{template_id}`** - Actualizar plantilla
- **`DELETE /{template_id}`** - Eliminar plantilla

### 🔄 Webhooks (`/api/webhooks/`)

- **`POST /ycloud`** - Webhook de YCloud para mensajes

## 🗄️ Base de Datos

### Modelos Principales

- **`Chat`** - Conversaciones con clientes
- **`Message`** - Mensajes individuales
- **`User`** - Usuarios del sistema
- **`Company`** - Empresas cliente
- **`Role`** - Roles de usuario
- **`Template`** - Plantillas de mensajes
- **`ChatSummary`** - Resúmenes generados por IA
- **`Appointment`** - Citas programadas

## 🤖 Servicios de IA

### Gemini AI Integration

- **Análisis de sentimientos** - Clasificación positiva/neutral/negativa
- **Detección de intenciones** - Compra, agendar, soporte, etc.
- **Extracción de entidades** - Montos, fechas, nombres
- **Sugerencias de acciones** - Próximos pasos recomendados
- **Generación de respuestas** - Respuestas sugeridas
- **Análisis de riesgo** - Probabilidad de abandono

## ⚙️ Configuración

### Variables de Entorno Requeridas

```bash
# API Keys
GEMINI_API_KEY=tu_api_key_de_gemini

# Base de datos
SQLITE_PATH=./data/app.db

# Configuración del servidor
APP_NAME=SibarConnect API
API_PREFIX=/api
SERVER_URL=http://localhost:8000
PUBLIC_URL=http://localhost:8000

# Usuario administrador
ADMIN_EMAIL=admin@sibarconnect.com
ADMIN_PASSWORD=admin123
```

## 🚀 Ejecución

### Instalación de Dependencias

```bash
pip install -r requirements.txt
```

### Ejecución del Servidor

```bash
python run.py
```

El servidor se ejecutará en `http://localhost:8000`

## 📊 Funcionalidades Principales

### 1. Gestión de Chats

- Creación y gestión de conversaciones
- Asignación a agentes
- Estados y prioridades
- Sistema de etiquetas y notas

### 2. Análisis de IA

- Insights automáticos de conversaciones
- Resúmenes inteligentes
- Asistencia en redacción
- Análisis de sentimientos

### 3. Gestión de Usuarios

- Sistema de roles y permisos
- Gestión de empresas
- Autenticación segura

### 4. Integración WhatsApp

- Importación de conversaciones
- Manejo de archivos multimedia
- Webhooks para mensajes entrantes

## 🔧 Mantenimiento

### Scripts de Utilidad

- **`create_admin.py`** - Crear usuario administrador inicial
- **`migrate_*.py`** - Scripts de migración de base de datos

### Logs y Monitoreo

- Logs detallados de operaciones
- Manejo de errores con mensajes descriptivos
- Validación de datos con Pydantic

## 🚨 Solución de Problemas

### Error 500 en Insights

- Verificar que `GEMINI_API_KEY` esté configurada
- Comprobar conexión a internet
- Revisar logs del servidor

### Problemas de Base de Datos

- Verificar permisos de escritura en `/data/`
- Ejecutar scripts de migración si es necesario
- Comprobar integridad de la base SQLite

## 📝 Notas de Desarrollo

- **FastAPI** para APIs rápidas y documentación automática
- **SQLAlchemy** para ORM robusto
- **Pydantic** para validación de datos
- **Google Gemini AI** para análisis de conversaciones
- **WebSockets** para comunicación en tiempo real
