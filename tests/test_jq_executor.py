import unittest
import shutil
from rexi.data_providers.jq_executor import JqExecutor

class TestJqExecutor(unittest.TestCase):
    def setUp(self):
        self.executor = JqExecutor()
        self.jq_available = shutil.which("jq") is not None

    def test_is_available(self):
        self.assertEqual(self.executor.is_available(), self.jq_available)

    def test_execute_identity(self):
        if not self.jq_available:
            self.skipTest("jq not installed")
        
        json_input = '{"key": "value"}'
        output, error = self.executor.execute(".", json_input)
        
        self.assertIsNone(error)
        self.assertIn('"key": "value"', output)

    def test_execute_filter(self):
        if not self.jq_available:
            self.skipTest("jq not installed")
            
        json_input = '{"users": [{"name": "Alice"}, {"name": "Bob"}]}'
        output, error = self.executor.execute(".users[].name", json_input)
        
        self.assertIsNone(error)
        self.assertIn('"Alice"', output)
        self.assertIn('"Bob"', output)

    def test_execute_invalid_json(self):
        if not self.jq_available:
            self.skipTest("jq not installed")
            
        json_input = 'invalid json'
        output, error = self.executor.execute(".", json_input)
        
        self.assertIsNotNone(error)
        self.assertIsNone(output)

    def test_execute_invalid_filter(self):
        if not self.jq_available:
            self.skipTest("jq not installed")
            
        json_input = '{"key": "value"}'
        output, error = self.executor.execute(".[", json_input)
        
        self.assertIsNotNone(error)
        self.assertIsNone(output)

if __name__ == "__main__":
    unittest.main()
