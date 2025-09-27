#!/usr/bin/env python3
"""
Test runner for the Option Wheel Strategy project.
"""
import sys
import os
import unittest

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'option_wheel_strategy'))

def run_tests():
    """Run all tests in the tests directory."""
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(start_dir, pattern='test*.py')
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)