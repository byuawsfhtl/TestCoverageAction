#!/usr/bin/env python3
"""
Edge case tests for TestChecker.py
"""

import unittest
import os
import sys
import subprocess
from unittest.mock import Mock, patch, mock_open
from argparse import Namespace

# Add the parent directory to the path so we can import TestChecker
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from TestChecker import CoverageChecker


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error scenarios."""
    
    def test_invalid_minimum_coverage_string(self):
        """Test handling of invalid minimum coverage values."""
        args = Namespace(
            minimum_coverage='invalid',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        
        with self.assertRaises(ValueError):
            CoverageChecker(args)
            
    def test_negative_minimum_coverage(self):
        """Test handling of negative minimum coverage."""
        args = Namespace(
            minimum_coverage='-10',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        
        checker = CoverageChecker(args)
        self.assertEqual(checker.minimum_coverage, -10.0)

class TestSubprocessErrors(unittest.TestCase):
    """Test subprocess execution errors."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        self.checker = CoverageChecker(self.test_args)
        
    @patch('subprocess.run')
    def test_run_tests_subprocess_error(self, mock_subprocess):
        """Test handling of subprocess.CalledProcessError during test execution."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'coverage')
        
        success, output = self.checker.run_tests_with_coverage(['test_file.py'])
        
        self.assertFalse(success)
        self.assertIn("Error running tests", output)
        
    @patch('subprocess.run')
    def test_run_tests_file_not_found(self, mock_subprocess):
        """Test handling of FileNotFoundError when coverage tool is missing."""
        mock_subprocess.side_effect = FileNotFoundError("coverage command not found")
        
        success, output = self.checker.run_tests_with_coverage(['test_file.py'])
        
        self.assertFalse(success)
        self.assertEqual(output, "Coverage tool not found")


class TestReportFormats(unittest.TestCase):
    """Test different report format handling."""
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('builtins.open', mock_open(read_data='{"totals": {"percent_covered": 85.0}}'))
    def test_html_report_format(self, mock_exists, mock_subprocess):
        """Test HTML report format generation."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='html'
        )
        checker = CoverageChecker(args)
        
        mock_exists.return_value = True
        mock_subprocess.return_value = Mock(stdout="HTML report generated")
        
        coverage_percentage, report_output = checker.generate_coverage_report()
        
        self.assertEqual(coverage_percentage, 85.0)
        self.assertEqual(report_output, "HTML report generated")
        
        # Check that the correct command was called for HTML
        calls = mock_subprocess.call_args_list
        html_call = next((call for call in calls if 'html' in str(call)), None)
        self.assertIsNotNone(html_call)
        
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('builtins.open', mock_open(read_data='{"totals": {"percent_covered": 72.5}}'))
    def test_xml_report_format(self, mock_exists, mock_subprocess):
        """Test XML report format generation."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='xml'
        )
        checker = CoverageChecker(args)
        
        mock_exists.return_value = True
        mock_subprocess.return_value = Mock(stdout="XML report generated")
        
        coverage_percentage, report_output = checker.generate_coverage_report()
        
        self.assertEqual(coverage_percentage, 72.5)
        self.assertEqual(report_output, "XML report generated")


class TestComplexFileStructures(unittest.TestCase):
    """Test complex file and directory structures."""
    
    def test_deeply_nested_test_files(self):
        """Test finding test files in deeply nested directories."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='**/test_*.py',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = CoverageChecker(args)
        
        # Mock glob.glob to simulate deeply nested files
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = [
                'level1/level2/level3/test_deep.py',
                'another/path/test_nested.py'
            ]
            
            # Mock os.path.isfile to return True for our test files
            with patch('os.path.isfile', return_value=True):
                test_files = checker.find_test_files()
                
            # Convert to relative paths for comparison
            found_files = {os.path.relpath(f, checker.workspace_path).replace(os.sep, '/') for f in test_files}
                
            self.assertEqual(len(test_files), 2)
            self.assertIn('level1/level2/level3/test_deep.py', found_files)
            self.assertIn('another/path/test_nested.py', found_files)
            
    def test_mixed_file_and_directory_paths(self):
        """Test handling mixed file and directory paths in test_paths."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/,specific/test_file.py,**/test_*.py',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = CoverageChecker(args)
        
        with patch('os.path.isdir') as mock_isdir, \
             patch('os.path.isfile') as mock_isfile, \
             patch('os.walk') as mock_walk, \
             patch('glob.glob') as mock_glob:
            
            # Setup mocks
            mock_isdir.side_effect = lambda path: path.endswith('tests/')
            mock_isfile.side_effect = lambda path: path.endswith('.py')
            mock_walk.return_value = [
                ('tests', [], ['test_from_dir.py', 'not_a_test_file.py'])
            ]
            mock_glob.return_value = ['other/test_glob.py']
            
            test_files = checker.find_test_files()
            
            # Convert absolute paths to relative paths for comparison
            found_files = {os.path.relpath(f, checker.workspace_path).replace(os.sep, '/') for f in test_files}
            
            # Should find files from directory walk, specific file, and glob
            expected_files = {
                'tests/test_from_dir.py',
                'specific/test_file.py', 
                'other/test_glob.py'
            }
            self.assertEqual(found_files, expected_files)


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery and graceful degradation."""
    
    def test_partial_coverage_data_missing(self):
        """Test handling when coverage JSON has missing data."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = CoverageChecker(args)
        
        # Test with missing 'totals' key
        with patch('subprocess.run'), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{"summary": "no totals key"}')):
            
            coverage_percentage, report_output = checker.generate_coverage_report()
            
            self.assertEqual(coverage_percentage, 0.0)
            
        # Test with missing 'percent_covered' key
        with patch('subprocess.run'), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{"totals": {"lines_covered": 100}}')):
            
            coverage_percentage, report_output = checker.generate_coverage_report()
            
            self.assertEqual(coverage_percentage, 0.0)
            
    @patch('subprocess.run')  
    def test_report_generation_failure_recovery(self, mock_subprocess):
        """Test recovery when detailed report generation fails."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = CoverageChecker(args)
        
        # Mock successful JSON generation but failed detailed report
        def side_effect(*args, **kwargs):
            if 'json' in args[0]:
                return Mock()  # Success for JSON
            else:
                raise subprocess.CalledProcessError(1, 'coverage report')
                
        mock_subprocess.side_effect = side_effect
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{"totals": {"percent_covered": 75.0}}')):
            
            coverage_percentage, report_output = checker.generate_coverage_report()
            
            self.assertEqual(coverage_percentage, 75.0)
            self.assertEqual(report_output, "Could not generate detailed report")


class TestGitHubActionsIntegration(unittest.TestCase):
    """Test GitHub Actions specific functionality."""
    
    @patch.dict(os.environ, {}, clear=True)
    def test_github_outputs_missing_env_var(self):
        """Test behavior when GITHUB_OUTPUT environment variable is missing."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = CoverageChecker(args)
        
        # Should not raise an exception
        checker.set_github_outputs(85.0, 5)
        
    @patch.dict(os.environ, {'GITHUB_OUTPUT': '/tmp/readonly_file'})
    @patch('builtins.open')
    def test_github_outputs_file_write_error(self, mock_open_func):
        """Test handling of file write errors for GitHub outputs."""
        mock_open_func.side_effect = PermissionError("Permission denied")
        
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = CoverageChecker(args)
        
        # Should not raise an exception, just print error
        checker.set_github_outputs(85.0, 5)


if __name__ == '__main__':
    unittest.main(verbosity=2) 