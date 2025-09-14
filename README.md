# Intune macOS Tools

Terminal UI for managing macOS apps and devices in Microsoft Intune. Focuses on a simple, group‑first app assignment workflow.

## What It Does

- Group-first app assignment: select Azure AD groups, then select apps, and apply one intent (required/available/uninstall) to all combinations at once.
- View and search macOS apps and groups with basic details.
- Basic device and dashboard views to support assignment workflows.

## Requirements

- Python 3.8+
- Access to a Microsoft Intune tenant and Azure AD permissions
- macOS, Linux, or Windows terminal

## Setup

1. Install uv
   - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows: `winget install --id AstralSoftware.Uv -e`

2. Create and sync the environment
   - `uv sync`  (creates `.venv` and installs dependencies from `pyproject.toml`)

3. Run the app
   - `uv run python intune_tools.py`

Optional:
- Activate the virtual environment: `source .venv/bin/activate` (PowerShell: `.venv\\Scripts\\Activate.ps1`) and run `python intune_tools.py`.
- Install optional groups:
  - Web features: `uv sync -E web`
  - Dev tools: `uv sync -E dev`

## Authentication

On launch, choose one of the following:

- Device code (no setup): authenticate in the browser using the Microsoft Graph public app.
- Browser login (no setup): opens a local browser window to sign in.
- Custom app (recommended for production): uses your own Entra ID app registration.

Custom app setup:

1. Create an app registration in Entra ID (Azure AD).
2. Grant Microsoft Graph permissions (minimum):
   - Interactive (device code or browser):
     - `DeviceManagementApps.ReadWrite.All`
     - `DeviceManagementManagedDevices.Read.All`
     - `DeviceManagementConfiguration.Read.All`
     - `Group.Read.All`
     - `User.Read`
   - App-only (client credentials):
     - `DeviceManagementApps.ReadWrite.All` (Application)
     - `DeviceManagementManagedDevices.Read.All` (Application)
     - `DeviceManagementConfiguration.Read.All` (Application)
     - `Group.Read.All` (Application)
   Note: The current UI calls `/me` after sign-in to display the user name. This is not available with app-only auth. If you use app-only, skip the user display step or sign in interactively.
3. Create a credentials file at either `./creds.json` or `~/.intune-tools/creds.json` using this format (see `example-creds.json`):

```
{
  "appId": "YOUR_APP_ID",
  "tenantId": "YOUR_TENANT_ID",
  "clientSecret": "YOUR_CLIENT_SECRET"
}
```

Start the app and select “Use Custom App (creds.json)”.

## Notes

- Settings are saved to `~/.intune-tools/config.json`.
- Credentials may be stored securely via the system keyring when using a custom app.
