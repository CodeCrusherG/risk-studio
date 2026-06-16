# Branding Configuration

Branding is configured per workspace. Without a local configuration, the application uses the Risk Studio name, colors, and assets.

## Public Default

When no local config exists, the app uses:

- platform name: `Risk Studio`
- browser title: `Risk Studio`
- primary color: `#317d59`
- main logo: `marvis/static/brand/risk-studio-mark.svg`
- welcome logo: `marvis/static/brand/risk-studio-mark.svg`
- favicon: `marvis/static/brand/risk-studio-icon-192.png`

## Local Private Config

Create this ignored file:

```text
workspace/branding/brand.json
```

Example:

```json
{
  "platform_name": "Credit Analytics",
  "browser_title": "Credit Analytics",
  "primary_color": "#1f6feb",
  "logo": "private-logo.svg",
  "favicon": "private-logo.svg",
  "validator_aliases": {
    "Reviewer One": "Credit Reviewer",
    "Reviewer Two": "Model Reviewer"
  }
}
```

`validator_aliases` maps a real validator name to the display alias shown as the
agent's name. It is optional and lives only in this private config, so real names
never ship in the public bundle. Entries are trimmed; empty or non-string values
are ignored. When unset, the agent simply shows `Agent`.

Put referenced files next to the config, for example:

```text
workspace/branding/private-logo.svg
```

The app exposes the active brand at `GET /api/branding` and serves local assets through `/branding/assets/...`.

`GET /` also injects the active workspace brand into the initial HTML response for the first paint: browser title, favicon, sidebar logo, welcome logo, platform name, and primary color tokens. The frontend still calls `GET /api/branding` after load as a runtime refresh/fallback, but the first visible frame should already match the active local config.

Keep private branding files in the workspace. Removing `workspace/branding/brand.json` restores the Risk Studio defaults.
