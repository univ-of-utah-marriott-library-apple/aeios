#!/bin/bash

if [ $EUID -ne 0 ]; then
    echo "run me as root" >&2
    #exit 1
fi

SITE_PACKAGES=/Library/Python/2.7/site-packages

DIRECTORIES=($SITE_PACKAGES/aeios 
             $SITE_PACKAGES/actools 
             "$HOME/Library/aeios")

FILES=("/usr/local/bin/aeiosutil"
       "/usr/local/bin/checkout_ipads.py"
       "$HOME/Library/Preferences/edu.utah.mlib.aeios.plist"
       "$HOME/Library/LaunchAgents/edu.utah.mlib.aeios.plist")

# recursively remove all directories
for d in "${DIRECTORIES[@]}"; do
    echo "> rm -rf '$d'"
    rm -rf "$d"
done

# remove all files
for f in "${FILES[@]}"; do
    echo "> rm -f '$f'"
    rm -rf "$f"
done

pkgutil --forget "edu.utah.mlib.aeios"