# Local Android / Termux dashboard deployment

This is the first local deployment path for the phone-only development setup. It runs the dashboard and private cTrader control API on the same Android device. Both bind to loopback only; they are not exposed to the Wi-Fi network or public internet.

## What you will get

- The XYFUSS dashboard opens in the phone browser at `http://127.0.0.1:4173`.
- Settings contains the cTrader account connection panel.
- The local control API reports whether server-side cTrader configuration is present.
- No Oracle Cloud host, public server, domain, or tunnel is needed just to view the dashboard.

This is a **local UI deployment**, not a completed remote OAuth deployment. cTrader's OAuth callback requires a publicly reachable HTTPS redirect URI registered with the approved cTrader application. Do not press Connect expecting OAuth to work until that public callback and server configuration exist.

## 1. Update the local repository

From Termux:

```bash
cd ~/xyfuss-forex-autopilot
git fetch origin feature/ctrader-account-auth-hardening
git switch feature/ctrader-account-auth-hardening
git pull --ff-only origin feature/ctrader-account-auth-hardening
```

If the branch does not exist locally yet, use:

```bash
git switch -c feature/ctrader-account-auth-hardening --track origin/feature/ctrader-account-auth-hardening
```

## 2. Build the dashboard

```bash
cd ~/xyfuss-forex-autopilot/apps/dashboard
npm install
npm run build
```

A successful build creates `apps/dashboard/dist/`.

## 3. Start the private control API

Open a second Termux session, then run:

```bash
cd ~/xyfuss-forex-autopilot
python -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; print('Encryption dependency: PASS')"
python scripts/run_control_plane.py
```

Expected message:

```text
XYFUSS cTrader control API listening privately on 127.0.0.1:8765
```

Leave this Termux session running. It binds only to localhost.

## 4. Start the dashboard

In the first Termux session:

```bash
cd ~/xyfuss-forex-autopilot/apps/dashboard
npm run preview:local
```

Expected address:

```text
http://127.0.0.1:4173
```

Open that address in the browser on the same phone. Select **Settings** → **Broker account connection**.

The connection status should say **Server setup required** until the private cTrader application settings are configured. This is expected at this stage.

## Stop the services

Press `CTRL+C` in each Termux session.

## Important

- Do not bind the API to `0.0.0.0` or forward port 8765 from your router.
- Do not put the cTrader Client Secret or encryption key in frontend code, Git, screenshots, or chat.
- Do not use the phone's local address as the cTrader OAuth redirect URI; cTrader needs the exact public HTTPS callback registered in the approved application.
- This local dashboard is a control-panel preview. It is not connected to the Rust trading engine, live market prices, or order execution.
