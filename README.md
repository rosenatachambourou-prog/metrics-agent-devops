# System Metrics Agent — Conteneurisation et CI/CD

![CI/CD](https://github.com/rosenatachambourou-prog/metrics-agent-devops/actions/workflows/ci-cd.yml/badge.svg)

Projet du cours « Éléments du DevOps » (Master, IAI) : conteneurisation, orchestration
et pipeline CI/CD de l'application `system_metrics_agent`.

## Équipe

| Membre | Rôle                                      | Machine                               |
| ------ | ----------------------------------------- | ------------------------------------- |
| Serge  | Dockerfiles, Compose, déploiement, README | MacBook Air M4 (arm64)                |
| Rose   | Tests, CI/CD, qualité du dépôt            | HP EliteBook 840 (x86_64, Windows 10) |
| Loïc   | Empêché par une panne matérielle          | MacBook Air M1 (arm64)                |

## Présentation et architecture

Deux processus issus de la **même image** : une API FastAPI qui reçoit les métriques
(`/health`, `/metrics`, `/metrics/latest`) et un agent qui collecte CPU, mémoire et
charge système, puis les envoie à l'API. Seule la commande de démarrage diffère.

```text
agent (python -m app.agent)  ──►  http://api:8000/metrics  ──►  api (uvicorn)
                     réseau Docker « metrics-net »
```

## Prérequis

- Docker Desktop, ou Docker Engine + Compose v2 (`docker version`, `docker compose version`)
- Un compte GitHub et un compte Docker Hub
- Sous Windows : Docker Desktop avec WSL 2 ; mémoire réglée dans `%UserProfile%\.wslconfig`
- Python 3.12 uniquement pour lancer les tests hors conteneur

## Lancer en développement

```bash
cp .env.example .env
docker compose up -d --build
```

Compose fusionne automatiquement `docker-compose.override.yml` : les deux services
utilisent l'image `metrics-agent:dev`, le code est monté en volume et `uvicorn`
tourne avec `--reload`. Toute modification dans `app/` déclenche
`WatchFiles detected changes... Reloading...`.

Tests dans le conteneur :

```bash
docker compose exec api pytest -q
```

## Lancer en production

### Build local

```bash
docker compose -f docker-compose.yaml up -d --build
curl http://localhost:8000/health
```

Le `-f docker-compose.yaml` explicite évite de charger l'override de développement.

### Depuis Docker Hub

<!-- TODO après la première publication par la CI -->

## Pipeline CI/CD

<!-- TODO : rédigé par Rose -->

## Images Docker Hub

<!-- TODO : lien vers hub.docker.com/r/rose000/metrics-agent -->

## Choix techniques et difficultés rencontrées

- **Image de base `python:3.12-slim`** (Debian, glibc) : toutes les dépendances
  s'installent en paquets précompilés.
- **Build multi-stage** : l'image finale ne contient que l'environnement virtuel et
  le dossier `app/` — 283 Mo sur disque, 61 Mo compressés.
- **Paquet `procps` ajouté** : `app/collector.py` appelle la commande `uptime`,
  absente de l'image slim. Sans lui, l'agent échouait à chaque cycle.
- **Utilisateur non-root** (UID 10001) et healthcheck écrit en Python, `curl`
  n'existant pas dans l'image slim.
- **`127.0.0.1` ne fonctionne pas entre conteneurs** : l'agent vise `http://api:8000/metrics`.
- **Aucun test dans le dépôt fourni** : la suite `pytest` a été écrite, et un
  `pytest.ini` ajouté pour que `pytest -q` trouve le module `app`.

## Captures

<!-- TODO : pipeline vert, pipeline rouge, docker compose ps, appel /health -->
