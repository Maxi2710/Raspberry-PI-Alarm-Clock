# Raspberry Pi Alarm Clock
A alarm clock made of a raspberry pi, some python code and a bit of 3D printing

## Features

- Set and manage alarms through physical buttons and a web interface
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
<br/>

### 2. Set timezone and Sync Time

change the timezone accordingly
```bash
sudo timedatectl set-timezone Europe/Berlin
sudo apt install ntp -y
```

<br/>

### 3. Install Python

```bash
sudo apt install python3.6  # Or use the latest available version
```
<br/>

### 4. Install and Configure Web Server (NGINX + PHP)

```bash
sudo apt install nginx php php-fpm -y
```

Modify the config file:
```bash
sudo nano /etc/nginx/sites-enabled/default
```

- Uncomment or add the following block:
    ```nginx
    location ~ \.php$ {
    include snippets/fastcgi-php.conf;
    fastcgi_pass unix:/run/php/php-fpm.sock;
    }
    ```
  
- Modify the index directive:
    ```nginx
    index index.php index.html index.htm index.nginx-debian.html;
    ```

Restart NGINX:
```bash
sudo service nginx restart
```
<br/>

### 5. Enable I2C Interface (for LCD Display)

```bash
sudo raspi-config
```

Navigate to: ```5 Interfacing Options ```
<br/>
Select: ``` P5 I2C ```
<br/>
Confirm with Yes, then OK and Finish

Install the LCD library:
```bash
sudo reboot
git clone https://github.com/dbrgn/RPLCD.git
cd RPLCD
sudo python3 setup.py install
sudo reboot
```

<br/>

### 6. Clone and Set Up This Project
(Comming soon)

<br/>

---

## Optional: Increase File Upload Limits (for larger audio files)

### PHP Configuration:

Set these values (replace ```version``` with your actual PHP version):
```bash
sudo nano /etc/php/version/fpm/php.ini
```

Change the upload filesize to someting larger:
```ini
upload_max_filesize = 200M
post_max_size = 200M
```

Restart services:
```bash
sudo service nginx restart
```
<br/>

### NGINX Configuration

```bash
sudo nano /etc/nginx/nginx.conf
```

Inseide the http block, add:
```bash
client_max_body_size 200M;
```

Restart NGINX again:
```bash
sudo service nginx restart
```

<br/>

### This message is for my IT teacher
Wir haben uns entschiedenen einen Wecker zu bauen, da dies nach einem Bestellsystem das Einzige war, was uns eingefallen ist. Desweiteren hat Finn im Moment keinen richtigen Wecker und wollte Diesen dann auch für sich privat verwenden. 
