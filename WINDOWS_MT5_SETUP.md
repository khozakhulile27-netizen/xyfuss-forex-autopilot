# Windows MetaTrader 5 Deployment Guide

This guide prepares Xyfuss Forex Autopilot for a Windows computer using the existing demo-only MT5 adapter. It does not enable live trading and does not place orders.

## Installation requirements

Install:

- Windows 10 or Windows 11, 64-bit
- The official MetaTrader 5 desktop terminal
- Python 3.10 or newer
- Microsoft Visual C++ Redistributable if required by Python packages
- Network access to the configured Exness demo server

`requirements.txt` installs the `MetaTrader5` package only when `platform_system == "Windows"`.

## Install MetaTrader 5

1. Install and open the official MetaTrader 5 terminal.
2. Sign in to the intended Exness demo account.
3. Confirm the exact demo server name shown in MetaTrader 5.
4. Keep the terminal running while executing the verifier.
5. Do not enable live execution.

## Install Xyfuss

From PowerShell in the repository directory:

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation:

```powershell
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Check dependencies

```powershell
.venv\Scripts\python.exe scripts\check_windows_mt5.py
```

This check reports the operating system, Python version, required package availability, and whether the Python MT5 module imports. It does not authenticate to a broker or place orders.

## Configure environment variables securely

Do not put credentials in source files, `config.yaml`, `config.example.yaml`, reports, shell scripts, screenshots, Git, or shell history.

For temporary process use in PowerShell 7, masked input can supply values without displaying them:

```powershell
$env:MT5_DEMO_LOGIN = Read-Host "Demo login" -MaskInput
$env:MT5_DEMO_PASSWORD = Read-Host "Demo password" -MaskInput
$env:MT5_DEMO_SERVER = Read-Host "Demo server" -MaskInput
```

The variables exist only in that PowerShell process and processes started from it. Masked input only hides terminal display; confirm the target shell and terminal are controlled and trusted.

For persistent user configuration, use Windows **Environment Variables** settings and add:

- `MT5_DEMO_LOGIN`
- `MT5_DEMO_PASSWORD`
- `MT5_DEMO_SERVER`

Protect the Windows account, close unnecessary terminals, and restart PowerShell after changing persistent variables.

GitHub Codespaces Secrets can provide variables in Codespaces, but they do not provide the Windows desktop or a running MetaTrader 5 terminal.

## Verify demo connection without placing an order

With MetaTrader 5 running and all three variables set:

```powershell
.venv\Scripts\python.exe scripts\verify_mt5_demo.py
```

The verifier:

- Reads `MT5_DEMO_LOGIN`, `MT5_DEMO_PASSWORD`, and `MT5_DEMO_SERVER`.
- Uses the existing MT5 demo adapter with live execution disabled.
- Connects and reconnects.
- Retrieves EUR/USD and GBP/USD prices.
- Checks connection health.
- Places no orders.

## Keep live trading disabled

Do not enable:

- `XYFUSS_LIVE_TRADING_ENABLED=true`
- `XYFUSS_LIVE_TRADING_APPROVAL=I_UNDERSTAND_LIVE_TRADING`

Keep configuration at `trading_mode: paper` and `live_trading_enabled: false`.

## Troubleshooting

### MetaTrader5 cannot be imported

Confirm Windows 64-bit, Python 64-bit, MetaTrader 5 64-bit, and reinstall:

```powershell
.venv\Scripts\python.exe -m pip install --force-reinstall -r requirements.txt
```

### MetaTrader 5 initialization fails

- Confirm the desktop terminal is running.
- Confirm the login belongs to the intended demo account.
- Confirm the server matches the terminal exactly.
- Confirm demo credentials are correct.
- Try opening or selecting the matching account in the desktop terminal.

### A server is rejected

The adapter only accepts server names containing `demo` or `trial`. Verify that the configured server is an Exness demo/trial server rather than a live server.
