# Deploy kinderagi — arhitectura pe două niveluri

## Nivelul 1 — kinderagi.com (public) = landing static, GitHub Pages, GRATUIT

Landing-ul din `docs/` se publică prin GitHub Pages. Nu are chat — e fața
onestă a proiectului: ce este, ce NU este, cum îl rulezi acasă.

**DNS la registrarul domeniului kinderagi.com:**

| Tip   | Nume | Valoare |
|-------|------|---------|
| A     | @    | 185.199.108.153 |
| A     | @    | 185.199.109.153 |
| A     | @    | 185.199.110.153 |
| A     | @    | 185.199.111.153 |
| CNAME | www  | amidigiart.github.io |

GitHub emite automat certificatul HTTPS după propagarea DNS (minute–ore).

## Nivelul 2 — app.kinderagi.com (privat) = aplicația, pe VPS propriu

Chat-ul cu copii NU se expune public nesupravegheat (vezi README — limitele
oneste). Instanța pilot rulează cu `KINDERAGI_ACCESS_CODE` — doar familiile
care au primit codul intră.

### Pași (Hetzner CX22, ~€4/lună, Ubuntu 24.04)

```bash
# 1. pe VPS: docker + compose
curl -fsSL https://get.docker.com | sh

# 2. codul
git clone https://github.com/amidigiart/kinderagi-core && cd kinderagi-core/deploy
cp .env.example .env && nano .env      # PIN real + cod de acces!

# 3. DNS: A record  app.kinderagi.com -> IP-ul VPS-ului

# 4. porneste stack-ul (app + ollama + caddy cu HTTPS automat)
docker compose up -d --build

# 5. o singura data: descarca modelul local
docker compose exec ollama ollama pull gemma3:4b

# 6. verifica
curl https://app.kinderagi.com/api/health
```

### Notă de resurse
gemma3:4b pe CPU-ul unui CX22 (4 vCPU) răspunde în ~15–60 s — acceptabil
pentru pilot, nu pentru scară. Pentru mai mulți utilizatori: CX32/CX42 sau
un GPU mic. Local-first rămâne recomandarea: fiecare familie/școală cu
instanța ei = zero date centralizate.

### Backup
Volumul `app_data` conține jurnalul semnat și cheile notarului:
`docker run --rm -v deploy_app_data:/d -v $PWD:/b alpine tar czf /b/backup.tgz /d`
