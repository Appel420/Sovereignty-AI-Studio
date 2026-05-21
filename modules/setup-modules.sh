#!/bin/sh
# Initialize all Sovereignty platform integration submodules.
# Run once after cloning this repository.
set -e
git submodule update --init --recursive modules/familyguard
git submodule update --init --recursive modules/every-cloud-for-everyone
echo "Modules initialized:"
echo "  modules/familyguard            — FamilyGuard iOS/macOS safety companion"
echo "  modules/every-cloud-for-everyone — Universal cloud encryption library"
echo ""
echo "To update modules to latest:"
echo "  git submodule update --remote modules/familyguard"
echo "  git submodule update --remote modules/every-cloud-for-everyone"
