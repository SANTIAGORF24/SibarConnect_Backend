# SibarConnect Backend

## Descripción General

Backend de la aplicación SibarConnect desarrollado con FastAPI, proporcionando APIs para gestión de chats, usuarios, empresas y funcionalidades de IA.

## Estructura del Proyecto

### 📁 Directorios Principales

- `app/` - Código principal de la aplicación
- `data/` - Base de datos SQLite
- `media/` - Archivos multimedia (stickers, templates, uploads)
- `scripts/` - Scripts de utilidad y migración
- `tests/` - Pruebas unitarias

### 🔧 Configuración

- **Base de datos**: SQLite con archivo `app.db`
- **Puerto**: 8000 (por defecto)
- **API Prefix**: `/api`

## 🚀 Rutas de la API

### 🔐 Autenticación (`/api`)

- **POST** `/login` - Inicio de sesión de usuario

### 👥 Usuarios (`/api`)

- **GET** `/users` - Listar usuarios
- **POST** `/users` - Crear usuario
- **GET** `/users/{user_id}` - Obtener usuario específico
- **PUT** `/users/{user_id}` - Actualizar usuario
- **DELETE** `/users/{user_id}` - Eliminar usuario

### 🏢 Empresas (`/api`)

- **GET** `/companies` - Listar empresas
- **POST** `/companies` - Crear empresa
- **GET** `/companies/{company_id}` - Obtener empresa específica
- **PUT** `/companies/{company_id}` - Actualizar empresa
- **DELETE** `/companies/{company_id}` - Eliminar empresa

### 🎭 Roles (`/api`)

- **GET** `/roles` - Listar roles
- **POST** `/roles` - Crear rol
- **GET** `/roles/{role_id}` - Obtener rol específico
- **PUT** `/roles/{role_id}` - Actualizar rol
- **DELETE** `/roles/{role_id}` - Eliminar rol

### 💬 Chats (`/api/chats`)

#### 📝 Mensajes

- **GET** `/messages` - Listar mensajes de un chat
- **POST** `/messages` - Enviar mensaje
- **GET** `/messages/{message_id}` - Obtener mensaje específico
- **PUT** `/messages/{message_id}` - Actualizar mensaje
- **DELETE** `/messages/{message_id}` - Eliminar mensaje

#### 🏷️ Tags y Notas

- **GET** `/tags-notes` - Listar tags y notas
- **POST** `/tags-notes` - Crear tag o nota
- **PUT** `/tags-notes/{id}` - Actualizar tag o nota
- **DELETE** `/tags-notes/{id}` - Eliminar tag o nota

#### 📅 Citas

- **GET** `/appointments` - Listar citas
- **POST** `/appointments` - Crear cita
- **PUT** `/appointments/{id}` - Actualizar cita
- **DELETE** `/appointments/{id}` - Eliminar cita

#### 🎯 Gestión

- **GET** `/management` - Listar chats con filtros
- **POST** `/management/start` - Iniciar chat
- **PUT** `/management/{chat_id}` - Actualizar chat
- **DELETE** `/management/{chat_id}` - Eliminar chat

#### 📁 Importaciones

- **POST** `/imports/whatsapp` - Importar chats de WhatsApp
- **POST** `/imports/media` - Importar archivos multimedia

#### 🎨 Media

- **POST** `/media/upload` - Subir archivo multimedia
- **GET** `/media/{file_id}` - Obtener archivo multimedia
- **DELETE** `/media/{file_id}` - Eliminar archivo multimedia

#### 🚀 Inicio de Chat

- **POST** `/start` - Iniciar nueva conversación

#### 🤖 IA y Resúmenes

- **POST** `/summaries/generate` - Generar resumen de chat
- **GET** `/summaries/{chat_id}` - Obtener resumen de chat
- **POST** `/ai/insights` - Generar insights del chat
- **POST** `/ai/assist-draft` - Asistir en redacción de mensaje
- **POST** `/ai/assist-reply` - Asistir en respuesta automática

#### ⚡ Tiempo Real

- **GET** `/realtime/ws` - WebSocket para actualizaciones en tiempo real

### 🎨 Stickers (`/api/chats/stickers`)

- **GET** `/stickers` - Listar stickers de empresa
- **POST** `/stickers` - Crear sticker
- **GET** `/stickers/{sticker_id}` - Obtener sticker específico
- **PUT** `/stickers/{sticker_id}` - Actualizar sticker
- **DELETE** `/stickers/{sticker_id}` - Eliminar sticker

### 🔗 Webhooks (`/api/webhooks`)

- **POST** `/ycloud` - Webhook de YCloud para WhatsApp

### 📱 Media (`/api`)

- **GET** `/media/{company_id}/stickers/{filename}` - Servir stickers
- **GET** `/media/{company_id}/templates/{filename}` - Servir templates
- **GET** `/media/{company_id}/uploads/{filename}` - Servir archivos subidos

### 📋 Templates (`/api/templates`)

- **GET** `/templates` - Listar templates
- **POST** `/templates` - Crear template
- **GET** `/templates/{template_id}` - Obtener template específico
- **PUT** `/templates/{template_id}` - Actualizar template
- **DELETE** `/templates/{template_id}` - Eliminar template

## 🗄️ Base de Datos

### Tablas Principales

- `users` - Usuarios del sistema
- `companies` - Empresas registradas
- `roles` - Roles y permisos
- `chats` - Conversaciones de WhatsApp
- `messages` - Mensajes individuales
- `chat_summaries` - Resúmenes generados por IA
- `templates` - Plantillas de contenido
- `template_items` - Elementos de templates
- `stickers` - Stickers de empresa

## 🔑 Variables de Entorno

### Requeridas

- `GEMINI_API_KEY` - Clave API de Google Gemini para IA
- `DEEPSEEK_API_KEY` - Clave API de DeepSeek (opcional)

### Opcionales

- `APP_NAME` - Nombre de la aplicación (default: "SibarConnect API")
- `API_PREFIX` - Prefijo de la API (default: "/api")
- `SERVER_URL` - URL del servidor (default: "http://localhost:8000")
- `PUBLIC_URL` - URL pública para recursos
- `ADMIN_EMAIL` - Email del administrador
- `ADMIN_PASSWORD` - Contraseña del administrador

## 🚀 Ejecución

### Instalación de Dependencias

```bash
pip install -r requirements.txt
```

### Ejecución del Servidor

```bash
python run.py
```

### Scripts de Utilidad

- `create_admin.py` - Crear usuario administrador
- `create_stickers_table.py` - Crear tabla de stickers
- `migrate_add_attachment_url.py` - Migración para URLs de adjuntos
- `migrate_ycloud.py` - Migración para YCloud

## 🔍 Funcionalidades Principales

### 💬 Gestión de Chats

- Importación automática desde WhatsApp
- Resúmenes generados por IA
- Sistema de tags y notas
- Gestión de citas y recordatorios

### 🤖 Inteligencia Artificial

- Generación de resúmenes con Gemini
- Análisis de insights de conversaciones
- Asistencia en redacción de mensajes
- Respuestas automáticas inteligentes

### 📱 Integración WhatsApp

- Webhooks de YCloud
- Manejo de archivos multimedia
- Sistema de stickers personalizados
- Templates de mensajes

### 🔐 Seguridad

- Autenticación por sesiones
- Control de acceso por roles
- Validación de datos con Pydantic
- Middleware CORS configurado

## 📊 Monitoreo y Logs

- Logs detallados de operaciones
- Manejo de errores con HTTPException
- Validación de datos de entrada
- Respuestas estructuradas en JSON

## 🔧 Mantenimiento

- Migraciones automáticas de base de datos
- Verificación de integridad de tablas
- Creación automática de directorios de media
- Scripts de backup y restauración
