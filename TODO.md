# TODO - Plan de Mejoras del Editor de Vocabularios Oceanográficos

> **Fecha de análisis**: 2025-12-05
> **Estado del proyecto**: MVP funcional, requiere mejoras de producción

---

## 📊 Resumen Ejecutivo

El sistema es un editor web de vocabularios SKOS con funcionalidad básica completa, pero requiere mejoras críticas en seguridad, escalabilidad y experiencia de usuario antes de producción.

**Prioridad de implementación:**
- 🔴 **Crítico** (Seguridad & Estabilidad): 8 items
- 🟡 **Importante** (Funcionalidad & UX): 9 items
- 🟢 **Deseable** (Optimización): 7 items

---

## 🔴 FASE 1: Seguridad y Estabilidad (URGENTE)

### 1. Protección CSRF
**Prioridad:** 🔴 CRÍTICA
**Esfuerzo:** 2 horas
**Descripción:** Implementar tokens CSRF en todos los formularios

```python
# Instalar
pip install Flask-WTF

# Implementar en app.py
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# En templates
{{ csrf_token() }}
```

**Archivos afectados:**
- `requirements.txt`
- `app.py`
- `templates/partials/_edit_form.html`
- `templates/admin.html`

---

### 2. Gestión Segura de Secrets
**Prioridad:** 🔴 CRÍTICA
**Esfuerzo:** 30 minutos
**Descripción:** Eliminar secretos hardcodeados, usar variables de entorno

**Cambios:**
- Remover `SECRET_KEY=dev_secret_key` de `docker-compose.yml`
- Generar secret aleatorio con `python -c 'import secrets; print(secrets.token_hex(32))'`
- Documentar en README.md cómo generar secrets

**Archivos afectados:**
- `docker-compose.yml`
- `.env.example`
- `README.md`

---

### 3. Rate Limiting
**Prioridad:** 🔴 CRÍTICA
**Esfuerzo:** 1.5 horas
**Descripción:** Prevenir ataques de fuerza bruta y abuso de API

```python
# Instalar
pip install Flask-Limiter

# Implementar
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Aplicar a endpoints críticos
@limiter.limit("5 per minute")
@auth_bp.route('/login')
```

**Endpoints a proteger:**
- `/login`
- `/sparql` (10 queries/min)
- Endpoints de edición (30/min)

---

### 4. Sistema de Logging y Auditoría
**Prioridad:** 🔴 CRÍTICA
**Esfuerzo:** 3 horas
**Descripción:** Registrar acciones críticas para debugging y compliance

**Implementación:**
- Logs estructurados con `python-json-logger`
- Tabla `AuditLog` en BD para acciones de usuarios
- Log de: login/logout, ediciones, aprobaciones/rechazos
- Rotación de logs con `logging.handlers.RotatingFileHandler`

**Campos de AuditLog:**
```python
- id
- user_id
- action (create, update, delete, approve, reject)
- entity_type (term, vocabulary, change_request)
- entity_id
- old_value (JSONB)
- new_value (JSONB)
- ip_address
- timestamp
```

---

### 5. Manejo de Errores Personalizado
**Prioridad:** 🔴 ALTA
**Esfuerzo:** 1 hora
**Descripción:** Páginas de error amigables y logging de excepciones

```python
@app.errorhandler(404)
def not_found(e):
    app.logger.warning(f"404 Not Found: {request.url}")
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"500 Error: {str(e)}", exc_info=True)
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403
```

**Templates a crear:**
- `templates/errors/404.html`
- `templates/errors/500.html`
- `templates/errors/403.html`

---

### 6. Validación de Datos
**Prioridad:** 🔴 ALTA
**Esfuerzo:** 4 horas
**Descripción:** Validar todos los inputs con schemas

```python
# Instalar
pip install marshmallow

# Schemas de validación
from marshmallow import Schema, fields, validate

class TermUpdateSchema(Schema):
    pref_label_es = fields.Str(required=False, validate=validate.Length(max=500))
    pref_label_en = fields.Str(required=False, validate=validate.Length(max=500))
    definition_es = fields.Str(required=False)
    definition_en = fields.Str(required=False)

# Validar en endpoints
schema = TermUpdateSchema()
errors = schema.validate(request.form)
if errors:
    return jsonify(errors), 400
```

---

### 7. Sanitización de Queries SPARQL
**Prioridad:** 🔴 ALTA
**Esfuerzo:** 1 hora
**Descripción:** Prevenir SPARQL injection y queries maliciosas

```python
# En routes_sparql.py
import re

def validate_sparql_query(query):
    # Limitar operaciones peligrosas
    forbidden = ['DROP', 'INSERT', 'DELETE', 'LOAD', 'CLEAR', 'CREATE']
    if any(kw in query.upper() for kw in forbidden):
        raise ValueError("Query contains forbidden operations")

    # Limitar complejidad
    if len(query) > 10000:
        raise ValueError("Query too complex")

    return True
```

---

### 8. Optimización del Endpoint SPARQL
**Prioridad:** 🔴 ALTA
**Esfuerzo:** 2 horas
**Descripción:** Cachear grafos RDF para evitar reconstrucción constante

**Problema actual:** `routes_sparql.py:49-55` carga TODOS los vocabularios en cada query

**Solución:**
```python
from functools import lru_cache
from datetime import datetime

# Cache global con timestamp
_rdf_cache = {'graph': None, 'timestamp': None}
CACHE_TTL = 300  # 5 minutos

def get_full_graph():
    now = datetime.now()
    if (_rdf_cache['graph'] is None or
        _rdf_cache['timestamp'] is None or
        (now - _rdf_cache['timestamp']).seconds > CACHE_TTL):

        full_graph = rdflib.Graph()
        for vocab in Vocabulary.query.all():
            g = generate_rdf_graph(vocab.id)
            if g:
                full_graph += g

        _rdf_cache['graph'] = full_graph
        _rdf_cache['timestamp'] = now

    return _rdf_cache['graph']

# Invalidar cache en cambios
def invalidate_rdf_cache():
    _rdf_cache['graph'] = None
```

---

## 🟡 FASE 2: Funcionalidad Core

### 9. Sistema de Búsqueda
**Prioridad:** 🟡 ALTA
**Esfuerzo:** 4 horas
**Descripción:** Búsqueda full-text en términos

**Implementación:**
```python
# Búsqueda básica SQL
@vocab_bp.route('/vocab/<int:vocab_id>/search')
def search_terms(vocab_id):
    q = request.args.get('q', '')
    terms = Term.query.filter(
        Term.vocab_id == vocab_id,
        db.or_(
            Term.pref_label_es.ilike(f'%{q}%'),
            Term.pref_label_en.ilike(f'%{q}%'),
            Term.definition_es.ilike(f'%{q}%'),
            Term.concept_id.ilike(f'%{q}%')
        )
    ).all()
    return render_template('partials/_search_results.html', terms=terms)
```

**Mejora avanzada (Fase 3):**
- Índices GIN en PostgreSQL para búsqueda full-text
- Elasticsearch para búsqueda semántica

---

### 10. Paginación
**Prioridad:** 🟡 ALTA
**Esfuerzo:** 2 horas
**Descripción:** Paginación en listados de términos

```python
# En routes_vocab.py
page = request.args.get('page', 1, type=int)
per_page = 50

terms_paginated = Term.query.filter_by(vocab_id=vocab_id)\
    .order_by(Term.concept_id)\
    .paginate(page=page, per_page=per_page, error_out=False)

return render_template('vocab_editor.html',
                      terms=terms_paginated.items,
                      pagination=terms_paginated)
```

---

### 11. Versionamiento e Historial
**Prioridad:** 🟡 MEDIA
**Esfuerzo:** 6 horas
**Descripción:** Track de cambios históricos en términos

**Nueva tabla:**
```python
class TermHistory(db.Model):
    __tablename__ = 'term_history'
    id = db.Column(db.Integer, primary_key=True)
    term_id = db.Column(db.Integer, db.ForeignKey('terms.id'))
    version = db.Column(db.Integer)
    snapshot = db.Column(JSONB)  # Estado completo del término
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    change_description = db.Column(db.Text)
```

**Features:**
- Vista de historial por término
- Diff entre versiones
- Rollback a versión anterior (admin only)

---

### 12. Migraciones de Base de Datos
**Prioridad:** 🟡 ALTA
**Esfuerzo:** 1 hora
**Descripción:** Gestión profesional de esquema con Alembic

```bash
pip install Flask-Migrate

# Inicializar
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Workflow futuro
# 1. Modificar models.py
# 2. flask db migrate -m "Descripción del cambio"
# 3. flask db upgrade
```

---

### 13. Suite de Tests
**Prioridad:** 🟡 ALTA
**Esfuerzo:** 8 horas (cobertura básica)
**Descripción:** Tests unitarios y de integración

```bash
pip install pytest pytest-flask pytest-cov

# Estructura
tests/
  ├── conftest.py          # Fixtures
  ├── test_models.py       # Tests de modelos
  ├── test_auth.py         # Tests de autenticación
  ├── test_vocab.py        # Tests de vocabularios
  ├── test_admin.py        # Tests de admin
  └── test_sparql.py       # Tests de SPARQL

# Ejecutar
pytest --cov=. --cov-report=html
```

**Cobertura mínima objetivo:** 70%

---

### 14. OAuth Mejorado
**Prioridad:** 🟡 MEDIA
**Esfuerzo:** 3 horas
**Descripción:** Mejoras en autenticación

**Cambios:**
- Soporte para múltiples proveedores (Google, GitHub, ORCID)
- Primer usuario registrado = admin automático
- Página de login con opciones (no redirect directo)
- Manejo de errores de OAuth
- Refresh tokens

---

### 15. API REST JSON
**Prioridad:** 🟡 MEDIA
**Esfuerzo:** 6 horas
**Descripción:** API RESTful con documentación Swagger

```python
pip install flask-restx

# Endpoints
GET    /api/vocabularies
GET    /api/vocabularies/{id}
GET    /api/vocabularies/{id}/terms
GET    /api/terms/{id}
POST   /api/terms             # Crear change request
PUT    /api/terms/{id}        # Crear change request
DELETE /api/terms/{id}        # Crear change request

# Admin endpoints
GET    /api/change-requests
POST   /api/change-requests/{id}/approve
POST   /api/change-requests/{id}/reject
```

**Autenticación API:** JWT tokens o API keys

---

### 16. Edición Completa de Términos
**Prioridad:** 🟡 MEDIA
**Esfuerzo:** 4 horas
**Descripción:** Formularios completos para todas las propiedades SKOS

**Campos faltantes en UI:**
- `alt_labels` (etiquetas alternativas)
- `related` (términos relacionados)
- `exact_match` (mapeos externos)
- Selector visual para `broader`/`narrower`

---

### 17. Sistema de Notificaciones
**Prioridad:** 🟡 BAJA
**Esfuerzo:** 5 horas
**Descripción:** Notificar a usuarios sobre cambios en sus requests

**Opciones:**
- Email con Flask-Mail
- Notificaciones in-app (tabla `Notification`)
- WebSocket para real-time (Flask-SocketIO)

**Triggers:**
- Change request aprobado/rechazado
- Término editado por admin (notificar a watchers)
- Nuevo comentario en change request

---

## 🟢 FASE 3: Escalabilidad y Experiencia

### 18. Cache Avanzado
**Prioridad:** 🟢 MEDIA
**Esfuerzo:** 3 horas
**Descripción:** Redis para caching distribuido

```python
pip install Flask-Caching redis

# Configuración
cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
})

# Usar en vistas
@cache.cached(timeout=300, key_prefix='vocab_list')
def get_vocabularies():
    return Vocabulary.query.all()
```

---

### 19. CI/CD Pipeline
**Prioridad:** 🟢 ALTA
**Esfuerzo:** 4 horas
**Descripción:** GitHub Actions para tests y deploy

```yaml
# .github/workflows/ci.yml
name: CI/CD
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          docker-compose up -d db
          docker-compose run web pytest

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        # ... deploy steps
```

---

### 20. Actualización de Dependencias
**Prioridad:** 🟢 ALTA
**Esfuerzo:** 1 hora
**Descripción:** Actualizar librerías y auditoría de seguridad

```bash
# Auditar vulnerabilidades
pip install safety
safety check

# Actualizar
pip list --outdated
pip install --upgrade Flask Flask-SQLAlchemy rdflib

# Dependabot en GitHub
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

### 21. Importación Inteligente
**Prioridad:** 🟢 MEDIA
**Esfuerzo:** 6 horas
**Descripción:** Merge incremental y detección de cambios

**Features:**
- Detectar qué términos cambiaron (diff)
- Opción de merge vs. replace completo
- Reportes de importación (X añadidos, Y modificados, Z sin cambios)
- Soporte para JSON-LD, N-Triples
- Validación de RDF antes de importar

---

### 22. Triple Store Dedicado
**Prioridad:** 🟢 BAJA
**Esfuerzo:** 12 horas
**Descripción:** Apache Jena Fuseki para SPARQL real

**Cuándo implementar:** Cuando se tengan >100,000 triples

**Arquitectura:**
```
PostgreSQL: Datos operacionales (usuarios, change requests)
Fuseki: Store RDF para queries SPARQL
Sync: Job que exporta de Postgres a Fuseki cada 5 min
```

---

### 23. Búsqueda Semántica
**Prioridad:** 🟢 BAJA
**Esfuerzo:** 8 horas
**Descripción:** Elasticsearch con búsqueda avanzada

**Features:**
- Búsqueda difusa (fuzzy matching)
- Búsqueda por facetas (filtrar por vocabulario, status, etc.)
- Sugerencias autocomplete
- Búsqueda en definiciones con ranking

---

### 24. Editor Visual de Relaciones
**Prioridad:** 🟢 BAJA
**Esfuerzo:** 10 horas
**Descripción:** Graph visualization para relaciones entre términos

**Herramientas:**
- Cytoscape.js o D3.js para visualización
- Drag & drop para crear relaciones
- Vista de grafo completo del vocabulario

---

## 🚀 FASE 4: Producción Enterprise

### 25. Monitoreo y Observabilidad
**Prioridad:** 🟢 ALTA (para producción)
**Esfuerzo:** 6 horas

```python
pip install prometheus-flask-exporter

# Métricas
- Request latency
- Error rates
- Vocabularies/Terms count
- Active users
- SPARQL query performance

# Stack recomendado
- Prometheus (métricas)
- Grafana (dashboards)
- Sentry (error tracking)
```

---

### 26. Multi-tenancy
**Prioridad:** 🟢 MEDIA
**Esfuerzo:** 16 horas
**Descripción:** Soporte para múltiples organizaciones

**Modelo:**
```python
class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    subdomain = db.Column(db.String(50), unique=True)

class User(db.Model):
    # ...
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))

# Todas las queries filtran por organization_id
```

---

### 27. Permisos Granulares
**Prioridad:** 🟢 MEDIA
**Esfuerzo:** 8 horas
**Descripción:** Permisos por vocabulario en vez de globales

**Tabla de permisos:**
```python
class VocabularyPermission(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    vocab_id = db.Column(db.Integer, db.ForeignKey('vocabularies.id'))
    permission = db.Column(db.String(20))  # view, edit, review, admin
```

---

### 28. Backup Automático
**Prioridad:** 🟢 ALTA (para producción)
**Esfuerzo:** 3 horas

```bash
# Cron job diario
0 2 * * * /app/scripts/backup.sh

# backup.sh
#!/bin/bash
# PostgreSQL dump
pg_dump $DATABASE_URL > /backups/db_$(date +%Y%m%d).sql

# Export RDF de todos los vocabularios
flask export-all-rdf --output /backups/rdf_$(date +%Y%m%d)

# S3 upload
aws s3 sync /backups s3://ocean-vocab-backups/
```

---

### 29. Documentación Completa
**Prioridad:** 🟢 ALTA
**Esfuerzo:** 12 horas

**Docs a crear:**
- `docs/architecture.md` - Arquitectura del sistema
- `docs/api.md` - Documentación de API
- `docs/deployment.md` - Guía de deployment
- `docs/development.md` - Guía para developers
- `docs/user_guide.md` - Manual de usuario
- Docstrings en todo el código Python
- Swagger UI para API REST

---

### 30. Responsividad Mobile
**Prioridad:** 🟢 MEDIA
**Esfuerzo:** 6 horas

**Mejoras UI:**
- Vista mobile optimizada para árbol de términos
- Hamburger menu
- Touch-friendly buttons
- Responsive tables (scroll horizontal)

---

## 🎯 Quick Wins (Impacto Alto, Esfuerzo Bajo)

Estas mejoras pueden implementarse en un día:

| # | Mejora | Tiempo | Impacto |
|---|--------|--------|---------|
| 2 | Secrets seguros | 30 min | 🔴 Crítico |
| 5 | Páginas de error | 1 hora | 🔴 Alto |
| 9 | Búsqueda básica | 2 horas | 🟡 Alto |
| 10 | Paginación | 2 horas | 🟡 Alto |
| 4 | Logging básico | 1 hora | 🔴 Alto |

**Total: ~7 horas de trabajo para 5 mejoras críticas**

---

## 📈 Roadmap Sugerido

### Sprint 1 (1 semana) - Seguridad
- Items #1-8 (Fase 1 completa)
- **Resultado:** Sistema seguro para deploy interno

### Sprint 2 (1 semana) - Funcionalidad Core
- Items #9-13
- **Resultado:** Sistema robusto con búsqueda, paginación, tests

### Sprint 3 (1 semana) - API y Edición
- Items #14-17
- **Resultado:** API REST, edición completa, notificaciones

### Sprint 4 (2 semanas) - Escalabilidad
- Items #18-24
- **Resultado:** Sistema escalable con caching, CI/CD, búsqueda avanzada

### Sprint 5 (2 semanas) - Producción
- Items #25-30
- **Resultado:** Sistema enterprise-ready

---

## 📝 Notas de Implementación

### Comandos útiles

```bash
# Iniciar desarrollo
docker-compose up -d
docker-compose exec web flask init-db
docker-compose exec web flask import-rdf

# Tests
docker-compose exec web pytest
docker-compose exec web pytest --cov

# Migraciones
docker-compose exec web flask db migrate -m "Add audit log"
docker-compose exec web flask db upgrade

# Backup
docker-compose exec db pg_dump -U postgres oceanvocab > backup.sql

# Auditoría de seguridad
pip install safety
safety check

# Linting
pip install black flake8
black .
flake8 .
```

---

## 🔗 Referencias

- [SKOS Primer](https://www.w3.org/TR/skos-primer/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [RDF/SKOS Validators](https://www.w3.org/2015/03/ShExValidata/)

---

## ✅ Checklist de Pre-Producción

Antes de deploy a producción, verificar:

- [ ] Todos los items de Fase 1 (Seguridad) completados
- [ ] Tests con >70% cobertura
- [ ] Migraciones de BD configuradas
- [ ] Secrets en variables de entorno (no hardcoded)
- [ ] Rate limiting activado
- [ ] Logging configurado
- [ ] Backup automático configurado
- [ ] Monitoreo activo (Sentry/Prometheus)
- [ ] SSL/TLS configurado
- [ ] Documentación actualizada
- [ ] Plan de rollback definido

---

**Última actualización:** 2025-12-05
**Mantenedor:** [Tu nombre/equipo]
