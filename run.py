#!/usr/bin/env python3
"""Run the MEXC Pump Detector.

Note: This runs the main detector only.
- To run main detector: python run.py OR python run_detector.py
- To run core detector: python run_core.py
- To run both: python run_all.py
"""

from src.main import main

if __name__ == "__main__":
    main()
