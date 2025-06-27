#!/bin/bash
"""
Simple build script for Linux users who prefer shell scripts
"""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}    Ogresync Linux AppImage Builder   ${NC}"
echo -e "${BLUE}======================================${NC}"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 is required but not installed${NC}"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "Ogresync.py" ]; then
    echo -e "${RED}[ERROR] Please run this script from the Ogresync root directory${NC}"
    exit 1
fi

# Run the Python build script
echo -e "${GREEN}Starting AppImage build...${NC}"
python3 linux-packaging/build_appimage.py "$@"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${YELLOW}Your AppImage is ready: linux-packaging/Ogresync-x86_64.AppImage${NC}"
else
    echo -e "${RED}Build failed with exit code $exit_code${NC}"
fi

exit $exit_code
