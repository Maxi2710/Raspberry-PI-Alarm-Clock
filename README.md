# Raspberry Pi Alarm Clock
A alarm clock made of a raspberry pi, some python code and a bit of 3D printing

## Features

- Set and manage alarms through a web interface
- Alarm playback with customizable audio
- Optional LCD display via I2C
- Built-in NGINX + PHP web server
- Works headless (no monitor required)

---

## Requirements

- Raspberry Pi with Raspberry Pi OS
- Python 3.6+ (preferably latest version)
- Aux compatible speaker
- Optional: LCD display (I2C-compatible)
- Internet access only for updates and time sync

---

## Setup Instructions

### 1. Update the System

Always begin with updating the Raspberry Pi:

```bash
sudo apt update && sudo apt upgrade -y
