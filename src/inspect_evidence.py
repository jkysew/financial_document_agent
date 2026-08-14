#!/usr/bin/env python3
"""
Simple command-line tool to inspect evidence from PDF documents.
"""

import os
import sys
from src.inspection_tool import smoke_test_inspection

def main():
    print("Running evidence inspection...")
    
    # Run smoke test
    result = smoke_test_inspection()
    
    if result:
        print(f"✓ Successfully created inspection file: {result}")
        print("You can now inspect the JSON output in the data/evidence/ directory")
    else:
        print("✗ Failed to create inspection file")
        sys.exit(1)

if __name__ == "__main__":
    main()