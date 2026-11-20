# cTrader account connection — operator setup

This is the first secure account-linking milestone for the XYFUSS dashboard. It uses cTrader's official OAuth approval page. The dashboard does **not** collect or display the cTrader password, Client Secret, access token, or refresh token.

## What this delivers

- The Settings page has a **Connect cTrader account** action and connection status.
- The operator is redirected to cTrader to sign in and approve **accounts (view-only)** permission.
- OAuth state is random, expires after ten minutes, and can be used once.
- The one-minute authorisation code is exchanged server-side.
- Access and refresh tokens are encrypted at rest with AES-256-GCM. The encryption key is kept outside the database and source control.
- Access tokens are refreshed server-side before expiry.
- The status API returns connection metadata only; it never returns token values.
- Disconnect removes the stored token record.

This is a demo/read-only account-linking milestone. It does not yet discover/select cTrader accounts, connect the Open API protobuf session, stream prices, or enable orders.

## 1. Register the cTrader application

1. Open the [cTrader Open API portal](https://openapi.ctrader.com/).
2. Create an application and wait for Spotware approval.
3. Choose the public HTTPS callback URL for your server, for example:

   `https://YOUR_PRIVATE_DOMAIN/api/v1/ctrader/callback`

4. Add that exact URL to the application's Redirect URIs.
5. Keep the Client ID and Client Secret private. Do not commit them to GitHub or paste them into ChatGPT.

The callback URL must match exactly, including scheme, hostname and path.

## 2. Configure the private XYFUSS server

Install the project dependencies in the server's Python environment, then set these environment variables in the server's secret manager or protected service configuration:

- `CTRADER_CLIENT_ID` — cTrader application Client ID.
- `CTRADER_CLIENT_SECRET` — cTrader application Client Secret.
- `CTRADER_REDIRECT_URI` — the exact HTTPS callback URL registered above.
- `XYFUSS_TOKEN_ENCRYPTION_KEY` — a fresh 32-byte URL-safe Base64 key.
- Optional: `XYFUSS_TOKEN_DATABASE` — defaults to `data/ctrader_tokens.sqlite3`.

Generate the encryption key on the server:

```bash
python -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Save the output directly in the server's secret manager. Keep a protected backup of the key separate from the encrypted SQLite database. If the key is lost, stored tokens cannot be decrypted and the account must be connected again.

Never put these values in `.env.example`, YAML committed to Git, frontend build variables, or browser storage.

## 3. Start the private control API

From the repository root, with the environment variables loaded:

```bash
python scripts/run_control_plane.py
```

By default it binds only to `127.0.0.1:8765`. It deliberately refuses a public network bind. Put it behind the same HTTPS reverse proxy as the dashboard.

The dashboard Vite development server proxies `/api` to `http://127.0.0.1:8765`. In production, configure the reverse proxy to forward the following paths to this private service:

- `GET /api/v1/ctrader/connect`
- `GET /api/v1/ctrader/callback` — must be reachable by cTrader and must validate the one-time state.
- `GET /api/v1/ctrader/status`
- `POST /api/v1/ctrader/disconnect`

Protect the dashboard and the connect/status/disconnect routes with private operator authentication (for example, an authenticated VPN or reverse-proxy login). The callback is the only route that must be reachable from the cTrader redirect, and it is protected by the one-time OAuth state. Use HTTPS. Do not expose port 8765 directly to the internet.

## 4. Connect from the dashboard

1. Open the private XYFUSS dashboard.
2. Open **Settings**.
3. Press **Connect cTrader account**.
4. Sign in on the official cTrader page and approve view-only account access.
5. cTrader returns to the registered callback. Return to Settings and confirm that it reports **CONNECTED**.

If the application is not approved, the redirect URI is wrong, or the server is not configured, the dashboard reports that the service is unavailable or the authorisation failed. No credential is silently accepted.

## API behavior

- `GET /api/v1/ctrader/connect` returns a one-time cTrader authorization URL.
- `GET /api/v1/ctrader/callback?code=...&state=...` validates state and exchanges the short-lived code.
- `GET /api/v1/ctrader/status` returns only connection state, demo environment and token expiry.
- `POST /api/v1/ctrader/disconnect` deletes the encrypted token record.

## Important limitations

- This branch requests only `accounts` permission. It cannot place trades.
- The cTrader account list and account selection UI are the next milestone.
- The existing cTrader protobuf adapter is demo-only and still needs to be wired to the encrypted token service.
- The dashboard must be deployed behind private operator authentication before use. The small WSGI server is not an internet-facing production server.
- This milestone is not proof of trading readiness and does not promise profit.
