# metrics-agent-devops

Conteneurisation, orchestration et pipeline CI/CD d'une petite application de collecte de métriques.

> **Modalité** — le sujet prévoit un travail individuel. La réalisation en groupe a été validée au préalable avec l'enseignant. La répartition des tâches figure en fin de document.

## Équipe

| Membre | Rôle principal | Machine |
|---|---|---|
| MAVOUNGOU Serge Murlain | Images Docker, orchestration Compose, pipeline CI/CD, publication des images | MacBook Air M4, 32 Go (arm64) |
| Rose | Dépôt GitHub, relecture des pull requests, secrets, vérification amd64 | HP EliteBook 840, 8 Go, Windows 10 (amd64) |
| Loïc | Empêché en cours de projet (panne matérielle) — ses tâches ont été reprises par Serge | — |

---

## Présentation

L'application se compose de deux processus qui partagent **la même image** :

- **`api`** — service FastAPI servi par uvicorn, expose `/health` et `/metrics` sur le port 8000 ;
- **`agent`** — boucle de collecte qui relève les métriques de la machine et les envoie à l'API à intervalle régulier.

```
                 réseau Docker « metrics-net »
   ┌──────────────┐                      ┌──────────────┐
   │   agent      │ ──POST /metrics──▶   │     api      │
   │ python -m    │                      │  uvicorn     │
   │  app.agent   │                      │ app.api:app  │
   └──────────────┘                      └──────┬───────┘
                                                │ 8000
                                                ▼
                                          hôte : localhost:8000
```

L'agent joint l'API par le **nom de service Compose** (`http://api:8000/metrics`), jamais par une adresse IP : la résolution DNS interne au réseau Docker s'en charge.

### Arborescence

```
.
├── app/                         code de l'application
├── tests/                       tests unitaires (pytest)
├── docs/captures/               captures d'écran du rendu
├── Dockerfile                   image de production (multi-stage)
├── Dockerfile.dev               image de développement (rechargement à chaud)
├── docker-compose.yaml          pile de production
├── docker-compose.override.yml  surcouche de développement (fusionnée automatiquement)
├── requirements.txt             dépendances d'exécution
├── requirements-dev.txt         dépendances de test
├── .dockerignore
├── .env.example                 modèle de configuration (aucun secret)
├── pytest.ini
└── .github/workflows/ci-cd.yml
```

---

## Prérequis

- Docker Desktop (ou Docker Engine + Compose v2)
- Git
- Python 3.12 uniquement pour lancer les tests hors conteneur

Copier le modèle de configuration avant tout lancement :

```bash
cp .env.example .env
```

| Variable | Rôle | Valeur par défaut |
|---|---|---|
| `DOCKERHUB_USERNAME` | compte propriétaire de l'image à déployer | — (obligatoire, à renseigner dans `.env`) |
| `IMAGE_TAG` | tag à déployer (`latest` ou `sha-xxxxxxx`) | `latest` |
| `METRICS_ENDPOINT` | URL visée par l'agent | `http://api:8000/metrics` |
| `COLLECTION_INTERVAL` | période de collecte, en secondes | `5` |
| `REQUEST_TIMEOUT` | délai d'attente des requêtes, en secondes | `5` |

`.env` n'est **jamais** versionné : il figure dans `.gitignore` et dans `.dockerignore`.

---

## Lancer en développement

`docker-compose.override.yml` est fusionné automatiquement par Compose. Il construit `Dockerfile.dev`, monte le code en volume et active `--reload` : toute modification d'un fichier Python redémarre uvicorn sans reconstruire l'image.

```bash
docker compose up -d --build
docker compose logs -f api
```

Lancer les tests dans le conteneur de développement :

```bash
docker compose exec api pytest -q
```

Arrêter :

```bash
docker compose down
```

## Lancer en production (construction locale)

Il faut nommer explicitement le fichier de production, sinon la surcouche de développement est appliquée :

```bash
docker compose -f docker-compose.yaml up -d --build
curl -s http://localhost:8000/health
```

## Déployer depuis Docker Hub

C'est le scénario cible : **aucun code source n'est nécessaire**, seulement le fichier Compose et un `.env`.

```bash
mkdir deploiement && cd deploiement
curl -O https://raw.githubusercontent.com/rosenatachambourou-prog/metrics-agent-devops/main/docker-compose.yaml
```

Créer ensuite un `.env` contenant au minimum `DOCKERHUB_USERNAME`, `IMAGE_TAG`, `METRICS_ENDPOINT`, `COLLECTION_INTERVAL` et `REQUEST_TIMEOUT`, puis :

```bash
docker compose config --images
docker compose pull
docker compose up -d --no-build
```

`docker compose config --images` affiche l'image réellement retenue avant tout téléchargement. `--no-build` interdit toute reconstruction : si la pile démarre, c'est que l'image provient bien du registre.

Vérification :

```bash
docker compose ps
curl -s http://localhost:8000/health
docker compose logs --tail 15 agent
```

Attendu : `{"status":"ok"}` sur `/health`, et dans les logs de l'agent `Métriques envoyées avec succès. HTTP=201` à chaque intervalle.

> **Piège rencontré.** Compose applique l'ordre de priorité suivant : variables du shell **avant** fichier `.env`. Un `DOCKERHUB_USERNAME` hérité du terminal a fait tirer la mauvaise image malgré un `.env` correct. D'où le réflexe `docker compose config --images` avant tout déploiement.

---

## Pipeline CI/CD

Fichier : `.github/workflows/ci-cd.yml`. Déclenché sur `push` et `pull_request` vers `main`, plus lancement manuel.

Un seul job, `build-test-push`, dans cet ordre :

1. **Checkout** du code
2. **Préparation de Buildx**
3. **Build de l'image de production**, chargée sur le runner, pas encore publiée
4. **Installation de Python 3.12**
5. **Tests unitaires** (`pytest -q`)
6. **Test de l'image construite** — démarrage du conteneur et appel de `/health` en boucle jusqu'à réponse
7. **Connexion à Docker Hub** — *uniquement sur `main`*
8. **Génération des tags** (`latest` + `sha-xxxxxxx`) — *uniquement sur `main`*
9. **Préparation de QEMU** — *uniquement sur `main`*
10. **Publication multi-architecture** (`linux/amd64`, `linux/arm64`) — *uniquement sur `main`*

Les quatre dernières étapes portent la condition `if: github.ref == 'refs/heads/main'`. Conséquence : une pull request est construite et testée mais **ne peut rien publier**. Seul du code relu et fusionné atteint le registre.

Secrets utilisés (dépôt → Settings → Secrets and variables → Actions) :

| Secret | Contenu |
|---|---|
| `DOCKERHUB_USERNAME` | compte Docker Hub de publication |
| `DOCKERHUB_TOKEN` | jeton d'accès personnel Docker Hub, portée *Read & Write* |

Le nom d'utilisateur n'est pas une donnée sensible en soi — il figure dans le nom de l'image publique. Le passer tout de même en secret évite d'avoir à modifier le workflow si le compte de publication change, ce qui est arrivé une fois au cours du projet.

---

## Images publiées

| Dépôt | Tags | Architectures |
|---|---|---|
| `serge000/metrics-agent` | `latest`, `sha-e44a732` | `linux/amd64`, `linux/arm64` |

Vérifier le manifeste multi-architecture :

```bash
docker buildx imagetools inspect serge000/metrics-agent:latest
```

La sortie doit lister deux entrées `Platform`, une par architecture. Un client Docker tirant ce tag reçoit automatiquement la variante correspondant à sa machine.

---

## Choix techniques

**Image de base `python:3.12-slim`.** Compromis entre la taille et la compatibilité : contrairement à Alpine, elle repose sur la glibc, ce qui évite de recompiler les dépendances Python contenant des extensions C.

**Construction multi-stage.** L'étage `builder` crée un environnement virtuel dans `/opt/venv` et y installe les dépendances ; l'étage `runtime` ne copie que cet environnement. Les outils de compilation et le cache pip restent dans l'étage intermédiaire. Résultat : **283 Mo** sur disque, **61 Mo** compressés au registre.

**`procps` installé explicitement.** L'image slim ne fournit pas la commande `uptime`, dont `app/collector.py` a besoin. Un seul `apt-get` suivi de la suppression des listes de paquets dans la même instruction `RUN`, pour ne pas figer le cache apt dans une couche.

**Exécution sans privilèges.** Un utilisateur système `app` (UID/GID 10001) est créé, sans dossier personnel et avec `/usr/sbin/nologin` comme interpréteur. `USER 10001:10001` est déclaré avant `CMD` : le processus n'est jamais root dans le conteneur.

**Sonde de santé en Python.** L'image slim ne contient pas `curl`. Le `HEALTHCHECK` appelle donc `urllib.request` : aucun paquet supplémentaire à installer. Le service `agent` désactive sa propre sonde (`healthcheck: disable: true`) puisqu'il n'expose aucun port.

**`depends_on: condition: service_healthy`.** L'agent n'est démarré qu'une fois l'API déclarée saine, sinon ses premières requêtes échoueraient.

**uvicorn sur `0.0.0.0`.** Lié à `127.0.0.1`, le serveur ne serait joignable que depuis l'intérieur du conteneur, et la publication de port n'aurait aucun effet.

**Une seule image pour les deux services.** `api` et `agent` partagent le même code ; seule la commande de lancement diffère. Une image unique, c'est un seul build, un seul tag et une cohérence garantie entre les deux processus.

**`pytest` retiré de `requirements.txt`.** Les dépendances de test vivent dans `requirements-dev.txt` : l'image de production n'embarque aucun outil de test.

**`pytest.ini` avec `pythonpath = .`.** Sans ce réglage, `pytest` lancé directement ne trouve pas le paquet `app` (seul `python -m pytest` fonctionne, car il ajoute le dossier courant au chemin d'import). Le fichier de configuration rend le comportement identique en local et en CI.

**Publication multi-architecture.** L'équipe travaille sur arm64 (Apple Silicon) et amd64 (Windows) ; les runners GitHub sont en amd64. Sans QEMU, l'image publiée ne fonctionnerait que sur l'une des deux familles de machines.

---

## Sécurité

- Aucun secret dans le dépôt : `.env` est ignoré par Git et par Docker, seul `.env.example` est versionné et il ne contient aucune valeur sensible.
- `.dockerignore` exclut `.env`, `.env.*`, `.git`, `.github`, `__pycache__/`, `.venv/` — ni l'historique Git ni les secrets locaux n'entrent dans le contexte de build.
- L'authentification à Docker Hub se fait par jeton d'accès personnel révocable, jamais par mot de passe de compte.
- Le conteneur s'exécute sous un utilisateur non privilégié.
- La publication est conditionnée à la branche `main`, donc à une pull request relue et fusionnée.

**Limite assumée.** Le dépôt appartient à Rose, et GitHub ne propose pas de rôle administrateur sur un dépôt personnel : seule la propriétaire peut écrire les secrets. Le pipeline publie donc sous le compte `serge000`, dont le jeton a été transmis une seule fois à Rose puis révoqué après le rendu. Une organisation GitHub aurait évité ce partage, chaque membre y gérant ses propres secrets.

Contrôle avant rendu — aucune trace de jeton dans l'historique :

```bash
git log -p --all -- . ':!README.md' | grep -nE "dckr_pat_"
```

La commande ne doit rien afficher. Le README est exclu de la recherche puisqu'il mentionne lui-même le préfixe des jetons.

---

## Captures

<!-- Déposer les fichiers dans docs/captures/ puis remplacer chaque ligne par une image. -->

| # | Contenu |
|---|---|
| 1 | Pile de développement : rechargement à chaud après modification d'un fichier |
| 2 | Pile de production : conteneur `api` à l'état *healthy* |
| 3 | Pipeline vert sur `main` |
| 4 | Pipeline rouge provoqué par un test cassé |
| 5 | Dépôt Docker Hub : tags `latest` et `sha-xxxxxxx` |
| 6 | Dossier de déploiement sans code source (`ls -a` + `docker images`) |
| 7 | `docker compose config --images`, puis `pull` et `up` depuis le registre |
| 8 | Logs de l'agent : `Métriques envoyées avec succès. HTTP=201` |

---

## Répartition du travail

| Tâche | Auteur | Relecture | PR |
|---|---|---|---|
| Séparation des dépendances, `pytest.ini` | Serge | Rose | — |
| `.dockerignore` et `Dockerfile` de production | Serge | Rose | #1 |
| `Dockerfile.dev` | Serge | Rose | #2 |
| `docker-compose.yaml` | Serge | Rose | #3 |
| `docker-compose.override.yml` et `.env.example` | Serge | Rose | #4 |
| Pipeline CI/CD | Serge | Rose | #6 |
| README | Serge | Rose | #7 |
| Dépôt, droits, secrets, protection de `main` | Rose | — | — |
| Vérification de l'image sur amd64 | Rose | — | — |

Toutes les contributions sont passées par une branche dédiée et une pull request relue avant fusion dans `main`.
