# CL API Troubleshooting

This script is for quickly rebooting all connected Arcus devices.

Usage:
```bash
uv run main.py
```

Or with custom mDNS scan timeout or delay between each device:
```bash
uv run main.py --mdns-timeout 5 --delay 1
```

See `--help` for details
