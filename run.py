import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402
from app.gpio_button import start_button_listener  # noqa: E402

app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    # Guard against the Werkzeug reloader (debug mode) starting this twice
    # in two processes.
    if not debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_button_listener(app)

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)
