# Deploying the PARALLAX backend — free, with your own domain

This deploys the **API + worker + Postgres + Redis + MinIO** on one always-free
VM, fronted by **Caddy** (automatic HTTPS), with the LLM served by the **AI/ML
API** gateway. It runs the **static + cortex** pipeline (no GPU, no Android
emulator) — the path proven on the live Alien run. The Vercel dashboard then
talks to it over HTTPS.

> The dynamic/emulator stage needs nested virtualization (KVM) and stays a
> local/on-prem capability. Band agents run separately (their own venv).

---

## 0. What you'll need (all free)
- **Oracle Cloud "Always Free"** account → an Ampere **ARM VM** (up to 4 vCPU /
  24 GB, free forever). Card required for signup, **not charged** on Always-Free.
- Your **GitHub Student Pack domain** (Namecheap `.me` or name.com). One DNS
  record turns it into `api.yourdomain` with a real TLS cert.
- Your **AI/ML API key** (the one already in your local `.env`).

*(Alternatives if you skip Oracle: Fly.io free allowance, or a "managed free
pieces" combo — Neon Postgres + Upstash Redis + Cloudflare R2. The single VM is
simplest and matches these files.)*

---

## 1. Create the VM (Oracle Always Free)
1. Oracle Cloud Console → **Compute → Instances → Create instance**.
2. Image: **Ubuntu 22.04**. Shape: **VM.Standard.A1.Flex** (Ampere ARM) →
   set **2–4 OCPU / 12–24 GB** (all within Always-Free).
3. Add your SSH public key. Create. Note the **public IP**.
4. **Open the firewall (cloud side):** VCN → the instance's **Security List** →
   add **Ingress rules**: source `0.0.0.0/0`, TCP ports **80** and **443**.

## 2. Point your domain at the VM
In **Namecheap** (Student Pack domain): *Domain List → Manage → Advanced DNS →
Add New Record*:
- Type **A Record**, Host **`api`**, Value **`<your VM public IP>`**, TTL Automatic.

(name.com: *Manage → DNS Records → Add* an A record for `api`.) Propagation is
usually a minute or two — check with `ping api.yourdomain`.

## 3. Prep the VM
```bash
ssh ubuntu@<VM-IP>
git clone https://github.com/arjun7n9s/Parallax.git && cd Parallax/parallax
git checkout feat/band-integration
bash deploy/bootstrap.sh          # installs Docker, opens host 80/443
# log out/in once so docker works without sudo
```

## 4. Configure secrets
```bash
cp .env.prod.example .env.prod
nano .env.prod
```
Set at minimum:
- `API_DOMAIN=api.yourdomain` and `ACME_EMAIL=you@…`
- `ALLOWED_ORIGINS=["https://parallax-mocha-beta.vercel.app","https://api.yourdomain"]`
- `API_KEY`, `ADMIN_API_KEY`, `WEBHOOK_SECRET` → `openssl rand -hex 24` for each
- `AIML_API=<your AI/ML API key>`
- `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD` → strong values

## 5. Launch
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```
First build takes a few minutes on ARM. Then verify:
```bash
curl https://api.yourdomain/health          # {"status":"ok","service":"PARALLAX",...}
docker compose -f docker-compose.prod.yml logs -f api worker
```
Caddy fetches the TLS cert automatically on first request to your domain.

## 6. Point the dashboard at it
In **Vercel** → the `parallax` project → **Settings → Environment Variables**:
- `VITE_API_BASE = https://api.yourdomain/api/v1`  → **Redeploy**.

Open the site → **Analyst Console** → sign in with your `API_KEY`. The dashboard
now streams live submissions; drag an APK to run the real pipeline.

---

## Operate
- **Update:** `git pull && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`
- **Logs:** `docker compose -f docker-compose.prod.yml logs -f`
- **Migrations** run automatically on API start (`alembic upgrade head`). To run
  manually: `docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head`
- **Stop / teardown:** `docker compose -f docker-compose.prod.yml down` (add `-v` to wipe data)

## Notes
- Want the graph/vector features? Add `neo4j` + `qdrant` services (see the dev
  `docker-compose.yml`) and set `NEO4J_*` / `QDRANT_*` in `.env.prod`. The cortex
  works without them.
- Postgres/Redis/MinIO are **not** exposed publicly — only Caddy (80/443) is.
- Cost: $0 for the VM (Always-Free) + your AI/ML API usage (~$0.16/APK).
