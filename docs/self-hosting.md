# Self-hosting the RISA Dashboard

For a national disaster management authority (NDMA), a partner or anyone else who needs a response's data held on their own server, in the country, with or without the internet. It is the same image as the consortium's instance at risa-dash.kobolabs.dev.

On a **kobo-in-a-box** field kit, don't follow this page: the box has its own RISA component (`remote/risa/` in kobo-in-a-box, with `risa.sh`), which wires the dashboard to the box's Kobo, map and fonts.

## What it needs

- A Linux server with Docker and Docker Compose. 4 CPU cores and 8 GB of RAM are comfortable; turning a large orthomosaic into a COG and printing page 1 at 300 dpi are the heavy jobs.
- Disk for the imagery, about twice its size (the original upload is kept next to the COG), plus room for bundles. The images are about 1.8 GB (the app) and 0.6 GB (PostGIS).
- A name people open it at, behind HTTPS, unless it only serves a trusted local network.

Three containers run from [`deploy/compose.yaml`](../deploy/compose.yaml): `db` (PostGIS), `web` (the API, the app and its guide; it migrates the database when it starts) and `worker` (jobs from a Postgres queue: imagery to COGs, printing, Kobo syncs, bundles). Files go on a Docker volume and are served with range requests, so there is no tile server.

## Install

```sh
git clone https://github.com/joshuaberetta/risa-dash.git && cd risa-dash
cp deploy/.env.example deploy/.env
```

Edit `deploy/.env`. At least:

| Setting | |
|---|---|
| `SECRET_KEY` | A long random string: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `TOKEN_KEY` | Another one. It encrypts the Kobo tokens responses connect with; without it they are encrypted with `SECRET_KEY`. Keep both: tokens can't be read without them |
| `POSTGRES_PASSWORD` | The database's password |
| `PUBLIC_URL` | Where people open it, e.g. `https://risa.ndma.gov.example` |
| `CREATE_KEY` | Needed to create or import a response. Set it unless everyone who can reach the server may |
| `ALLOWED_SERVERS` | The Kobo servers responses may connect to: kf and eu, or your own (`https://kobo.ndma.gov.example`). `http://` only for a server on a trusted network, listed exactly |

Then build and start:

```sh
docker compose -f deploy/compose.yaml --env-file deploy/.env up -d --build
```

The commands below use a shorthand for the compose call; define it in your shell first (bash or zsh):

```sh
dc() { docker compose -f deploy/compose.yaml --env-file deploy/.env "$@"; }
```

It listens on port 8000 (`RISA_PORT` to change it). `curl http://localhost:8000/api/config` answers once it's up. Every setting is in the README's [Settings](../README.md#settings) table and in `deploy/.env.example`.

## HTTPS and a proxy

Put it behind the proxy you already run. Uploads come in 8 MB parts, so allow request bodies of at least 10 MB, and long enough timeouts for a slow link. With nginx:

```nginx
server {
    listen 443 ssl;
    server_name risa.ndma.gov.example;
    # ssl_certificate ... ;

    client_max_body_size 20m;
    proxy_read_timeout 300s;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Or Caddy, which gets the certificate by itself:

```
risa.ndma.gov.example {
    request_body { max_size 20MB }
    reverse_proxy 127.0.0.1:8000
}
```

Publish port 8000 only to the proxy: `RISA_PORT=127.0.0.1:8000` in `deploy/.env`. The worker prints by opening the app inside the compose network (`http://web:8000`), not through the proxy.

## Files: on the server or in object storage

By default (`STORAGE=filesystem`) imagery, PDFs and bundles are on the `media` volume. To use S3-compatible object storage instead (MinIO, DigitalOcean Spaces, AWS S3), set `STORAGE=s3` and the `S3_*` settings in `deploy/.env.example`. COGs are then public-read under unguessable keys so browsers and QGIS read them straight from the bucket (`MEDIA_PUBLIC_URL` for a CDN in front); everything else is reached through short-lived signed links.

## With no internet

Nothing calls the internet at runtime except what's set below, so the same install works on a network with no way out. The CI runs it that way on every change (`scripts/e2e.sh`).

- **Basemaps.** `ONLINE_BASEMAPS=false` hides OpenFreeMap, Esri and OpenStreetMap. Offline basemaps are [PMTiles](https://docs.protomaps.com/pmtiles/) extracts of the area (made with `pmtiles extract` from a Protomaps build, while online). Any `*.pmtiles` file under `basemaps/` in the media volume is listed as a basemap, named after the file:

  ```sh
    dc exec web mkdir -p /data/media/basemaps
  dc cp Mozambique.pmtiles web:/data/media/basemaps/
  ```

- **Label fonts.** Map labels need glyphs from `GLYPHS_URL`, OpenFreeMap by default. Offline, point it at a tile server's fonts on your network (a [TileServer GL](https://github.com/maptiler/tileserver-gl) or [Martin](https://martin.maplibre.org) with fonts), and set `MAP_FONT` and `MAP_FONT_BOLD` to fonts it has. Protomaps' font set has no Bold, so with it use `MAP_FONT_BOLD=Noto Sans Medium`. Without fonts, the map and page 1 still show imagery, symbols and the printed text, but not the labels on the map.

- **Installing with no internet.** Build the image where there is a link, then carry it:

  ```sh
  docker compose -f deploy/compose.yaml --env-file deploy/.env build
  docker save risa-dash:latest postgis/postgis:16-3.5 | gzip > risa-images.tgz
  # on the server
  docker load < risa-images.tgz
  docker compose -f deploy/compose.yaml --env-file deploy/.env up -d
  ```

  On arm64 servers use `imresamu/postgis:16-3.5` (see the comment in `deploy/compose.yaml`).

- **Kobo.** List only your local Kobo server in `ALLOWED_SERVERS`.

## Access

There are no user accounts. Creating or importing a response needs the instance's `CREATE_KEY`, when set. Each response then has its own **edit key**, shown once when it's made; whoever has it can change that response. Viewing is open to anyone who has a response's link (links are unlisted and not indexed). `READ_ONLY_PUBLIC=false` makes viewing need the edit key too, for an instance that should show nothing without it.

## Moving responses in and out: bundles

A bundle is a whole response in one zip (see the README's [Response bundles](../README.md#what-works)). In the app: **Bundle** on a response's page, **Import bundle** on the home page. On the server, for a USB drive or a large archive:

```sh
# out
dc exec web python manage.py bundle export <response-slug> /tmp/response.risa.zip
dc cp web:/tmp/response.risa.zip /media/usb/
# in (no edit key needed on the command line)
dc cp /media/usb/response.risa.zip web:/tmp/
dc exec web python manage.py bundle import /tmp/response.risa.zip
```

`bundle export --no-imagery` leaves the orthomosaics out, to send only the work done on them to an instance that has the imagery already. Bundles aren't encrypted yet: treat a drive with one on it as sensitive.

## Backups

Three things: the database, the files, and `deploy/.env` (without its `SECRET_KEY` and `TOKEN_KEY`, the Kobo tokens in the database can't be read).

```sh
dc exec -T db pg_dump -U risa -Fc risa > risa-$(date +%F).dump
dc exec -T web tar cz -C /data/media --exclude=./bundles --exclude=./uploads . > risa-media-$(date +%F).tgz
cp deploy/.env risa-env-$(date +%F)
```

To restore on a new server, install as above with the same `deploy/.env`, then:

```sh
dc stop web worker
dc exec -T db pg_restore -U risa -d risa --clean --if-exists < risa-2026-11-11.dump
dc run --rm -T --no-deps web tar xz -C /data/media < risa-media-2026-11-11.tgz
dc start web worker
```

On `STORAGE=s3`, back up the bucket with the object store's own tools.

## Upgrades

```sh
git pull
docker compose -f deploy/compose.yaml --env-file deploy/.env up -d --build
```

`web` applies database migrations when it starts. Take a backup first. Jobs already queued wait in the database while the worker restarts.
