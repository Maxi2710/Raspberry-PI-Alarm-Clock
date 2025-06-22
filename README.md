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
```

### 2. Set timezone and Sync Time

```bash
sudo timedatectl set-timezone Europe/Berlin
sudo apt install ntp -y
```
change the timezone accordingly

### 3. Install Python

```bash
sudo apt install python3.6  # Or use the latest available version
```

### 4. Install and Configure Web Server (NGINX + PHP)

```bash
sudo apt install nginx php php-fpm -y
```

Modify the config file:
```bash
sudo nano /etc/nginx/sites-enabled/default
```
