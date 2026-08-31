# Smart Notice Board

A digital notice board system for a college, built with Flask + SQLite on the
backend and Tailwind CSS + vanilla JavaScript on the frontend. It's designed
to run on a Raspberry Pi 4B connected to a big screen (TV/monitor) in kiosk
mode.

- **Admin panel** — a single admin account (email/password issued by IT) logs
  in to create, edit, delete and publish/unpublish notices.
- **Notice board** — `/notice_board` is the only page students/the public
  screen ever load. It shows whatever is currently published, full-screen,
  in large readable type, and keeps showing it until the admin changes
  something. It polls the server every few seconds and updates itself live,
  so nobody ever needs to refresh the display.
- **Voice announce** — each notice has an "Announce" button that reads its
  title, date and description aloud through whatever audio output is
  connected to the device (e.g. a paired Bluetooth speaker), using the
  system `espeak-ng` text-to-speech engine.
- **Students + email alerts** — the admin panel has a Students section for
  adding students (name, enrollment number, email). Every time a notice is
  published, all students are emailed the title, date and description via
  SMTP.

## How it works

- Notices have a date, title, description and priority (Normal / Important /
  Urgent), and a Published/Draft state.
- Only **Published** notices ever appear on `/notice_board`.
- If more than one notice is published at once, the board rotates between
  them automatically (with a subtle fade), showing a dot indicator per
  notice. Urgent notices are sorted first.
- If nothing is published, the board shows a clean idle screen with the
  clock and college name instead of going blank.
- The board page never needs a manual reload: it polls a small JSON API
  (`/api/notices/board`) in the background and only re-renders when the
  published set actually changes.

## Project layout

```
app/
  __init__.py         Flask app factory, blueprint registration, `flask seed-admin` CLI
  config.py           Config from environment variables
  extensions.py       SQLAlchemy / Flask-Login / CSRF singletons
  models.py           Admin, Notice and Student models
  mailer.py           SMTP email alerts sent to students on publish
  auth/routes.py       /login, /logout
  admin/routes.py      /admin dashboard + JSON CRUD endpoints, students, announce (TTS)
  board/routes.py      /notice_board + /api/notices/board
  templates/           Jinja templates (Tailwind via CDN)
  static/js/admin.js    Admin dashboard interactivity (fetch-based CRUD, modals, toasts)
  static/js/students.js Students section interactivity
  static/js/board.js    Notice board polling, rotation, rendering
run.py                 Dev entrypoint
requirements.txt
.env.example           Copy to .env and fill in real values
```

## Local setup (Windows/Mac/Linux dev machine)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
copy .env.example .env        # Windows: copy, Mac/Linux: cp
```

Edit `.env` and set `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` (and
`ADMIN_NAME` if you like). Then create the database and the admin account:

```bash
set FLASK_APP=run.py                     # Windows (PowerShell: $env:FLASK_APP="run.py")
flask seed-admin
```

Run it:

```bash
python run.py
```

- Admin panel: http://localhost:5000/login
- Notice board: http://localhost:5000/notice_board

Re-running `flask seed-admin` at any time resets the admin's password to
whatever is in `.env` (or pass `--email`/`--password` flags directly) —
handy if credentials are ever forgotten.

## Deploying on the Raspberry Pi 4B

### 1. Install Python and the app

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip chromium-browser unclutter
git clone <your-repo-url> smart-notice-board   # or copy the folder over
cd smart-notice-board
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # set SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
```

Generate a real secret key instead of leaving the placeholder:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Seed the admin account:

```bash
export FLASK_APP=run.py
flask seed-admin
```

### 2. Run the server with gunicorn as a systemd service

Create `/etc/systemd/system/notice-board.service`:

```ini
[Unit]
Description=Smart Notice Board (Flask)
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/smart-notice-board
EnvironmentFile=/home/pi/smart-notice-board/.env
ExecStart=/home/pi/smart-notice-board/.venv/bin/gunicorn -w 2 -b 127.0.0.1:8000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now notice-board
sudo systemctl status notice-board
```

The app now runs on `http://127.0.0.1:8000` and restarts automatically on
boot or after a crash.

### 3. Auto-launch Chromium in kiosk mode on the big screen

Add an autostart entry so the Pi boots straight into the notice board,
full-screen, with no address bar, no cursor and no screen blanking.

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/notice-board.desktop
```

```ini
[Desktop Entry]
Type=Application
Name=Notice Board Kiosk
Exec=/home/pi/notice-board-kiosk.sh
X-GNOME-Autostart-enabled=true
```

`~/notice-board-kiosk.sh`:

```bash
#!/bin/bash
xset s off
xset -dpms
xset s noblank
unclutter -idle 0.5 -root &
chromium-browser --noerrdialogs --disable-infobars --kiosk \
  --incognito --check-for-update-interval=31536000 \
  http://127.0.0.1:8000/notice_board
```

```bash
chmod +x ~/notice-board-kiosk.sh
```

Reboot the Pi (`sudo reboot`) — it should come up with the notice board
filling the screen. Manage notices from any other device on the same
network by browsing to `http://<pi-ip-address>:8000/login` (put the Flask
app behind nginx/Caddy with HTTPS if the admin panel needs to be reachable
outside the trusted campus network).

### Fully offline Tailwind (optional)

Templates load Tailwind from the CDN (`cdn.tailwindcss.com`) for
simplicity, which needs internet access in the browser rendering the page.
If the Pi's display network is fully offline, replace the CDN `<script>`
tag in `app/templates/base.html` and `app/templates/board/notice_board.html`
with a locally compiled stylesheet using the standalone Tailwind CLI
(no Node.js required):

```bash
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-arm64
chmod +x tailwindcss-linux-arm64
./tailwindcss-linux-arm64 -i ./app/static/css/app.css -o ./app/static/css/tailwind.build.css --minify
```

Then swap the CDN `<script src="https://cdn.tailwindcss.com">` for
`<link rel="stylesheet" href="{{ url_for('static', filename='css/tailwind.build.css') }}">`.

## Voice announce (text-to-speech)

The "Announce" button on each notice calls the server, which speaks the
notice through whatever audio device is currently the system default —
a Bluetooth speaker if one is paired and set as default.

On the Pi, install the offline TTS engine and pair/set the speaker:

```bash
sudo apt install -y espeak-ng
bluetoothctl   # pair, trust and connect your speaker, then:
               # in a desktop session, set it as the default output device
               # in Sound Settings, or via `pactl set-default-sink <name>`
```

No internet connection or extra Python package is needed — it shells out
to `espeak-ng` directly. If it's not installed, the Announce button returns
a clear error instead of failing silently.

## Email alerts to students

Add students (name, enrollment number, email) from the Students tab in the
admin panel. Whenever a notice is published, every student is emailed the
title, date and description via SMTP.

Set these in `.env` (never commit real SMTP credentials):

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=1
SMTP_USERNAME=your-account@gmail.com
SMTP_PASSWORD=your-app-password   # Gmail: use an App Password, not your login password
MAIL_FROM=your-account@gmail.com
```

Leaving `SMTP_HOST` blank disables email alerts entirely — publishing still
works, the app just skips sending mail and logs that SMTP isn't configured.

## Security notes

- There is no self-service admin signup — accounts are created only via
  `flask seed-admin`, matching "IT issues the credentials" requirement.
- Passwords are hashed with Werkzeug's `generate_password_hash` (never
  stored in plaintext).
- All state-changing admin requests are protected by CSRF tokens
  (Flask-WTF), sent automatically by `admin.js`.
- `/notice_board` and its JSON API are read-only and require no
  authentication, by design — it's the public display endpoint.
