# Steinbach Pool — Home Assistant integration

Unofficial Home Assistant integration for [Steinbach](https://www.steinbach.at/)
pool heat pumps. Steinbach pumps are Tuya hardware, so this integration talks to
the officially supported **Tuya Cloud OpenAPI** using a (free) Tuya IoT cloud
project that you link to your Smart Life account.

It discovers your linked heat pump(s) automatically and exposes a climate entity
(power, mode, target temperature) plus inlet / outlet / ambient temperature
sensors and diagnostic sensors.

## Installation

### HACS (recommended)

1. In HACS, choose **Integrations → ⋯ → Custom repositories**.
2. Add `https://github.com/BirknerAlex/hacs_steinbach` with category **Integration**.
3. Install **Steinbach Pool** and restart Home Assistant.

### Manual

Copy `custom_components/steinbach` into your Home Assistant `config/custom_components/`
directory and restart Home Assistant.

## Setup

The integration authenticates with a Tuya IoT cloud project, not your Steinbach
app login. One-time setup:

1. **Pair the pump in Smart Life.** Install the **Smart Life** (or **Tuya
   Smart**) app, create an account in the same region you'll use (e.g. Europe),
   and add the heat pump. If it's bound to the Steinbach app, remove it there (or
   reset the Wi-Fi module) first.
2. **Create a Tuya IoT cloud project** at <https://iot.tuya.com> (free):
   *Cloud → Development → Create Cloud Project*, Development Method **Smart
   Home**, Data Center matching your app region (e.g. **Central Europe**). Note
   the **Access ID** and **Access Secret** from the project Overview.
3. **Authorize the API services** (project → *Service API* → *Go to Authorize*):
   IoT Core, Authorization Token Management, Device Status Notification, Smart
   Home Basic Service.
4. **Link your app account**: project → *Devices* → *Link App Account* → *Add App
   Account*, then scan the QR code from the Smart Life app (*Me* → scan icon).
   The pump appears under *Devices*.
5. **Set the device to controllable.** Linked devices default to **Read Only**;
   switch the pump to **Controllable** in the project's *Devices* tab — otherwise
   reads work but every command (power, mode, target temperature) silently fails.

Then in Home Assistant: **Settings → Devices & Services → Add integration →
Steinbach Pool**, and enter the **Access ID**, **Access Secret**, and **Region**
(e.g. `eu`).

> Tuya's free *IoT Core* service is a 1-month trial. Renew it (also free) before
> it expires or the integration will stop receiving data.

## How it works

The integration signs requests to the Tuya OpenAPI with your project's Access
Secret (HMAC-SHA256), fetches an access token (auto-refreshed before it expires),
and polls each linked device's properties on a configurable interval
(`cloud_polling`). Entities are built dynamically from each device's Tuya
**model**, so heat-pump models with a slightly different data-point set still get
sensible entities.

### Entities (Steinbach WP Startis Inverto / Silent Mini, Tuya `modelId e1ktcz2k`)

| DP code | Meaning | Entity |
|---------|---------|--------|
| `switch` / `mode` / `temp_set` / `temp_current` | power, mode, target & current temp | climate |
| `switch` | Power (also a standalone toggle) | switch |
| `mode` | Heat / cool (also a standalone selector) | select |
| `temp_set` | Target water temperature (also a standalone slider) | number |
| `inwt_temp` | Inlet water temperature | sensor |
| `outwt_temp` | Outlet water temperature | sensor |
| `whj_temp` | Ambient temperature | sensor |
| `return_temperature` | Suction-gas temperature | sensor (diagnostic) |
| `cmp_temp` | Discharge temperature | sensor (diagnostic) |
| `p_temp` | Coil temperature | sensor (diagnostic) |
| `operating_frequency` | Compressor frequency (Hz) | sensor (diagnostic) |
| `expansion_valve` | Expansion valve opening | sensor (diagnostic) |
| `fault` | Fault bitmap | binary sensor (problem) |

Unknown read-only numeric data points on other models are exposed as generic
diagnostic sensors rather than being dropped. The target temperature limits
(10–45 °C here) are read from the device model, so they match whatever your unit
reports.

Availability follows a successful cloud read rather than Tuya's device `online`
flag — that flag often reports *offline* while the pump is switched off, even
though the cloud still returns current values.

## Options

The poll interval is configurable via the integration's **Configure** dialog
(default 60 s).

## License

MIT — see [`LICENSE`](LICENSE).
