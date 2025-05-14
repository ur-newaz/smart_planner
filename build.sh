#!/usr/bin/env bash
# Exit on error
set -o errexit

# Set environment variables for PDF generation
export RENDER=true
export FLASK_ENV=production

# Check if wkhtmltopdf is available, as it may be pre-installed on Render
if ! command -v wkhtmltopdf &> /dev/null; then
    echo "wkhtmltopdf not found. PDF generation may not work correctly."
    echo "Setting up a simple PDF generation environment..."
    
    # Create a simple script that will fake wkhtmltopdf for testing purposes
    mkdir -p /tmp/bin
    echo '#!/bin/bash
echo "PDF generation is simulated on Render free tier"
touch "$2"  # Create empty PDF file
' > /tmp/bin/wkhtmltopdf-wrapper
    chmod +x /tmp/bin/wkhtmltopdf-wrapper
    export PATH="/tmp/bin:$PATH"
fi

# Upgrade pip and install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
python -m flask db upgrade 