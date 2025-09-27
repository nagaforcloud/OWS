# This file makes the Trading directory a proper Python package
# when running tests from within the Trading directory
import sys
import os

# Add the Trading directory to the Python path to allow relative imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))