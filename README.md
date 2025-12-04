# Editor de Vocabularios Oceanográficos

Sistema web para la gestión, visualización y edición de vocabularios controlados oceanográficos (SKOS).

## Características

*   **Gestión de Vocabularios**: Importación desde RDF/XML y visualización jerárquica.
*   **Edición Colaborativa**: Flujo de trabajo con roles (Admin, Revisor, Editor, Visualizador).
*   **Interfaz Moderna**: Diseño sobrio con soporte para modo oscuro/claro.
*   **Interoperabilidad**: Exportación a RDF, Turtle, CSV y punto de acceso SPARQL.
*   **Autenticación**: Integración con Google OAuth.

## Requisitos

*   Docker y Docker Compose (Recomendado)
*   O Python 3.10+ y PostgreSQL

## Instalación Rápida (Docker)

1.  Clonar el repositorio.
2.  Crear un archivo `.env` basado en `.env.example` con tus credenciales de Google.
3.  Ejecutar:
    ```bash
    docker-compose up -d --build
    ```
4.  Inicializar la base de datos (solo la primera vez):
    ```bash
    docker-compose exec web flask init-db
    ```
5.  Importar datos iniciales:
    ```bash
    docker-compose exec web flask import-rdf
    ```
6.  Acceder a `http://localhost:5000`.

## Estructura del Proyecto

*   `app.py`: Aplicación Flask principal.
*   `models.py`: Modelos de base de datos (SQLAlchemy).
*   `routes_*.py`: Controladores por módulo (vocab, admin, sparql).
*   `templates/`: Plantillas HTML (Jinja2 + TailwindCSS).
*   `utils/`: Utilidades de importación/exportación RDF.

## Licencia

[Tu Licencia Aquí]
