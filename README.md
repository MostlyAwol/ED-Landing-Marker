# PlanetPin MVP

A stand-alone Elite Dangerous planetary coordinate overlay.

It reads Elite Dangerous `Status.json` and recent journal `Scan` events, then draws a rough screen-space marker for a target latitude/longitude.

## What it does

- Shows a transparent always-on-top overlay.
- Lets you enter a target latitude and longitude.
- Draws one marker:
  - **solid circle** = target is likely on the visible side of the planet
  - **hollow circle** = target is likely over the horizon / far side
  - **EDGE** = projected marker is outside the current screen view and has been clamped to the edge

This is not a perfect AR projection. It assumes your ship/camera is roughly level and uses heading plus local planet geometry.

## Requirements

- Windows
- Python 3.11+
- Elite Dangerous running in borderless/windowed mode, not exclusive fullscreen

No external Python packages are required.

## Setup

1. Edit `config.json`.
2. Set `journal_dir` to your Elite Dangerous journal folder, usually:

```json
"C:/Users/YOUR_WINDOWS_USER/Saved Games/Frontier Developments/Elite Dangerous"
```

3. Run:

```bat
run.bat
```

Or:

```bat
python main.py
```

## In-game use

1. Enter your target latitude and longitude.
2. Fly near a landable planet.
3. Scan the planet if PlanetRadius is not available yet.
4. Keep the marker near the middle of your view as you approach.

## Calibration

Use the control window:

- `Horizontal FOV`: widen/narrow left-right placement.
- `Pitch offset`: moves the marker projection up/down by pretending the camera is pitched.

Start with:

```text
Horizontal FOV: 70
Pitch offset: 0
```

Then tune while flying toward a known coordinate.

## Known limitations

Elite Dangerous does not provide a perfect camera matrix through the journal/status files. This MVP does not know true camera pitch, roll, headlook, or exact FOV. It is meant as a rough landing guide, not a pixel-perfect AR system.

## Click-through overlay

The marker overlay is set to click-through on Windows, so mouse clicks should pass through to Elite Dangerous. The small PlanetPin control window is still clickable.

Use Elite Dangerous in borderless or windowed mode. Exclusive fullscreen may appear above the overlay or block it depending on Windows/GPU settings.
