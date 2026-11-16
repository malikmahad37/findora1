import os
from app import create_app

# Use the production config (reads DATABASE_URL from env)
app = create_app('production')

# Vercel expects a WSGI callable named "app"

if __name__ == "__main__":
    # Local testing only
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
