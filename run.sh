#!/bin/bash
# FRED-SOL Runner

cd "$(dirname "$0")"

case "$1" in
    scan)
        python3 scanner.py
        ;;
    wallet)
        python3 wallet.py
        ;;
    swap)
        python3 executor.py
        ;;
    loop)
        python3 main.py loop ${2:-60}
        ;;
    *)
        python3 main.py
        ;;
esac
