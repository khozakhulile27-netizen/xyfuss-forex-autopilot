# XYFUSS CLOUD presence integration

The Forex Autopilot can report its process presence to the local XYFUSS CLOUD
control plane. This is a heartbeat-only integration; it is not a broker
connection, market-data feed, trade instruction, or remote execution channel.

## Local Android / Termux setup

Start XYFUSS CLOUD first on the same phone. The Cloud API listens on loopback
at 127.0.0.1:8080.

Configure the Forex Autopilot process to read the shared Cloud token from a
private file:

    export XYFUSS_CLOUD_URL="http://127.0.0.1:8080"
    export XYFUSS_CLOUD_AGENT_TOKEN_FILE="$HOME/.config/xyfuss-cloud/agent.token"

Then start the dashboard locally:

    cd ~/xyfuss-forex-autopilot
    python -m xyfuss_forex_autopilot dashboard --host 127.0.0.1 --port 8000

The Cloud heartbeat starts only while the dashboard process is running. It
sends the fixed identity xyfuss-forex-autopilot, version metadata, and mode
paper every 60 seconds. It sends no broker credentials, account IDs, balances,
positions, orders, market data, or strategy details.

Cloud accepts this agent only in paper mode. The heartbeat is rejected if a
different mode is supplied. The Cloud service marks an agent offline after
180 seconds without a successful heartbeat.

The token file must contain the same secret configured as XYFUSS_API_TOKEN
for the Cloud process and should be readable only by the phone owner (chmod
600). Plain HTTP is accepted only for loopback; non-loopback Cloud URLs must
use HTTPS.

## What online means

An online heartbeat proves only that this Python dashboard process can reach
the Cloud API and authenticate. It does not prove that a broker is connected,
that market prices are live, that the scheduler is running a real strategy,
that a trade is safe, or that any profit is being made.

Live trading remains disabled. The heartbeat cannot place, modify, or close
orders and cannot remotely execute code.
