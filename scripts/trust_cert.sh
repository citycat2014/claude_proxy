#!/bin/bash
#
# Trust the mitmproxy CA certificate on macOS
#
# This script adds the mitmproxy CA certificate to the macOS System Keychain
# and exports environment variables for Python to trust it.
#

CERT_PATH="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"

echo "Claude Code Capture - Certificate Trust Script"
echo "==============================================="
echo ""

# Check if mitmproxy certificate exists
if [ ! -f "$CERT_PATH" ]; then
    echo "Certificate not found at: $CERT_PATH"
    echo ""
    echo "Please start the proxy first to generate the certificate:"
    echo "  python scripts/run.py start"
    echo ""
    exit 1
fi

echo "Found certificate at: $CERT_PATH"
echo ""

# Add certificate to System Keychain
echo "Adding certificate to System Keychain..."
echo "(You may be prompted for your password)"
echo ""

sudo security add-trusted-cert -d -r trustRoot \
    -k /Library/Keychains/System.keychain \
    "$CERT_PATH"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Certificate trusted successfully!"
    echo ""
    echo "IMPORTANT: For Python applications to trust the proxy, set these environment variables:"
    echo ""
    echo "  export SSL_CERT_FILE=$CERT_PATH"
    echo "  export REQUESTS_CA_BUNDLE=$CERT_PATH"
    echo "  export NODE_EXTRA_CA_CERTS=$CERT_PATH"
    echo ""
    echo "Add them to your shell profile (~/.zshrc) for persistence."
    echo ""
    echo "Then configure Claude Code to use the proxy:"
    echo "  export HTTPS_PROXY=http://127.0.0.1:8080"
    echo "  export HTTP_PROXY=http://127.0.0.1:8080"
    echo ""
else
    echo ""
    echo "✗ Failed to trust certificate"
    echo ""
    exit 1
fi