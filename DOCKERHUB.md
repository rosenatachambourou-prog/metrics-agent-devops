# System Metrics Agent & API

[![CI/CD Status](https://github.com/rosenatachambourou-prog/metrics-agent-devops/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/rosenatachambourou-prog/metrics-agent-devops/actions)
[![Platforms](https://img.shields.io/badge/platforms-amd64%20%7C%20arm64-blue.svg)](https://hub.docker.com/r/serge000/metrics-agent)
[![Live Demo](https://img.shields.io/badge/demo-Railway-success.svg)](https://metrics-agent.up.railway.app/health)

Application conteneurisée composée de deux processus complémentaires partageant **une même image minimale et sécurisée** :
- **`api`** : API FastAPI servie par Uvicorn qui expose `/health`, `/metrics` et `/metrics/latest` sur le port `8000`.
- **`agent`** : Démon de collecte périodique (CPU, RAM, charge système via `psutil` et `procps`) qui transmet les métriques au format JSON en HTTP à l'API.

- **Démo en production (Railway) :** [https://metrics-agent.up.railway.app/health](https://metrics-agent.up.railway.app/health)
- **Dépôt GitHub du projet :** [github.com/rosenatachambourou-prog/metrics-agent-devops](https://github.com/rosenatachambourou-prog/metrics-agent-devops).

---

## Architectures supportées

L'image est construite et publiée sous un manifeste multi-plateforme :
- **`linux/amd64`** (serveurs cloud, architectures x86_64, PC Windows / Linux)
- **`linux/arm64`** (Apple Silicon M1/M2/M3/M4, Raspberry Pi 64-bit, instances ARM cloud)

Docker sélectionne automatiquement la variante adaptée à votre machine lors du téléchargement (`docker pull`).

---

## Démarrage rapide

### 1. Lancer l'API seule (Production)

```bash
docker run -d \
  --name metrics-api \
  -p 8000:8000 \
  serge000/metrics-agent:latest
```

Vérifier la sonde de santé :
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

Consulter les dernières métriques enregistrées :
```bash
curl http://localhost:8000/metrics/latest
```

---

### 2. Lancer l'Agent seul

```bash
docker run -d \
  --name metrics-agent \
  -e METRICS_ENDPOINT="http://<adresse_api>:8000/metrics" \
  -e COLLECTION_INTERVAL="5" \
  serge000/metrics-agent:latest python -m app.agent
```

---

### 3. Orchestration complète avec Docker Compose

Créez un fichier `docker-compose.yaml` autonome :

```yaml
services:
  api:
    image: serge000/metrics-agent:latest
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - metrics-net
    restart: unless-stopped

  agent:
    image: serge000/metrics-agent:latest
    command: ["python", "-m", "app.agent"]
    environment:
      METRICS_ENDPOINT: http://api:8000/metrics
      COLLECTION_INTERVAL: 5
      REQUEST_TIMEOUT: 5
    depends_on:
      api:
        condition: service_healthy
    healthcheck:
      disable: true
    networks:
      - metrics-net
    restart: unless-stopped

networks:
  metrics-net:
    driver: bridge
```

Puis démarrez l'ensemble sans code source ni étape de compilation locale :
```bash
docker compose up -d
```

---

## Variables d'environnement

| Variable | Rôle | Valeur par défaut |
|---|---|---|
| `METRICS_ENDPOINT` | URL visée par l'agent de collecte | `http://127.0.0.1:8000/metrics` |
| `COLLECTION_INTERVAL` | Intervalle en secondes entre deux collectes | `5` |
| `REQUEST_TIMEOUT` | Délai d'expiration des requêtes HTTP (secondes) | `5` |

---

## Sécurité & Optimisations

- **Construction Multi-stage :** Les dépendances de compilation et le cache pip sont isolés dans l'étage de build intermédiaire.
- **Utilisateur non-privilégié :** L'application s'exécute sous un utilisateur dédié non-root (`UID 10001:10001`).
- **Sonde de santé Python :** Aucun utilitaire tiers (`curl`) requis dans l'image pour satisfaire le `HEALTHCHECK`.
- **Intégration continue :** Publication automatisée sur Docker Hub via GitHub Actions avec suite de tests unitaire bloquante (`pytest`).
