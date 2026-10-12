# Pilot gate (Clerk sign-in, allowlist, admin page)

Puts the register behind sign-in. Only approved users can view it; admins approve users and turn the gate on or off at `/admin/`.

## Files

| Path | What it is |
|---|---|
| `verifier.py` | Small Python service: checks Clerk sign-ins, the allowlist, admin rights and the on/off switch. Standard library only. |
| `nginx.conf` | Gated nginx site. Every page needs a pilot cookie except `/sign-in/`, `/_auth/login`, `/_auth/logout`, `/_auth/gate` and the crawler files. |
| `signin/` | Sign-in page (Clerk SDK, invite-only, no sign-up link). |
| `gate-admin/admin/` | Admin page: approve, remove, grant or revoke admin, turn the gate on or off. |

## Secrets and config (not in git)

Keep these outside the repository, for example in `~/register-auth/`:

- `cookie-secret`: random string that signs pilot cookies (mode 600).
- `clerk-secret`: the Clerk secret key (mode 600). Only the verifier reads it.
- `config/allowed-emails.txt`: one email per line.
- `config/admins.txt`: one email per line.
- `config/pilot-gate.json`: written by the admin page (`{"enabled": true|false}`).

## Run (Docker, no compose plugin needed)

```bash
docker network create register-net
docker run -d --name register-auth --network register-net --restart unless-stopped \
  -e CLERK_DOMAIN=<clerk frontend domain> -e CONFIG_DIR=/config \
  -v <repo>/deploy/pilot-gate/verifier.py:/app/verifier.py:ro \
  -v ~/register-auth/cookie-secret:/run/secrets/cookie-secret:ro \
  -v ~/register-auth/clerk-secret:/run/secrets/clerk-secret:ro \
  -v ~/register-auth/config:/config \
  python:3.12-slim python -I /app/verifier.py

docker run -d --name ai-safety-policy-register --network register-net --restart unless-stopped \
  -p 8090:80 \
  -v <repo>:/usr/share/nginx/html:ro \
  -v <repo>/deploy/pilot-gate/nginx.conf:/etc/nginx/conf.d/default.conf:ro \
  -v <repo>/deploy/pilot-gate/signin:/usr/share/nginx/signin:ro \
  -v <repo>/deploy/pilot-gate/gate-admin:/usr/share/nginx/gate-admin:ro \
  nginx:1.27.4-alpine
```

Set `SSL_CERT_FILE` and mount the host CA bundle too if outbound TLS to Clerk fails behind an interception proxy.

The sign-in page has the Clerk publishable key and domain in `signin/index.html`. Change them there if the Clerk instance changes. The Clerk secret key never goes in this folder, because nginx would serve it.

## Notes

- Clerk needs the public origin (for example `https://airegister.sushant.no`) in its allowed origins.
- Edits to single-file mounts (`verifier.py`, `nginx.conf`) need the container recreated. Replacing a file this way breaks the bind mount.
- Cloudflare or any shared cache must not store gated responses. The gate sends `Cache-Control: private, no-store`. Purge the cache after changing public files.
