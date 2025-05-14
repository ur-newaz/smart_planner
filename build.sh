#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install system dependencies required for wkhtmltopdf and WeasyPrint
apt-get update
apt-get install -y wkhtmltopdf xvfb libpango-1.0-0 libpangoft2-1.0-0 libfontconfig1

# Create symlink for xvfb-run as wkhtmltopdf wrapper to run headless
echo '#!/bin/bash
xvfb-run -a --server-args="-screen 0, 1024x768x24" /usr/bin/wkhtmltopdf "$@"
' > /usr/local/bin/wkhtmltopdf-wrapper
chmod +x /usr/local/bin/wkhtmltopdf-wrapper

# Set system environment variables
export FLASK_ENV=production
export RENDER=true

# Upgrade pip and install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations if needed
python -m flask db upgrade 