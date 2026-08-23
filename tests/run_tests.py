"""
Master test runner for Yefira Blender Plugin.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("dcc_plugins"))

def run_all_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_dir = os.path.dirname(__file__)
    for filename in sorted(os.listdir(test_dir)):
        if filename.startswith("test_") and filename.endswith(".py"):
            module_name = filename[:-3]
            try:
                mod = __import__(f"tests.{module_name}", fromlist=[module_name])
                suite.addTests(loader.loadTestsFromModule(mod))
            except Exception as e:
                print(f"Error loading {filename}: {e}")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    run_all_tests()
