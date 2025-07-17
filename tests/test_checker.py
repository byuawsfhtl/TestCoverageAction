#!/usr/bin/env python3
"""
Tests for TestChecker.py
"""

import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch, mock_open
from argparse import Namespace
import subprocess

# Add the parent directory to the path so we can import TestChecker
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from TestChecker import TestCoverageChecker, main


class TestTestCoverageChecker(unittest.TestCase):
    """Test the TestCoverageChecker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_args = Namespace(
            minimum_coverage='80',
            test_paths='tests/,**/test_*.py',
            source_paths='.',
            exclude_paths='tests/,setup.py',
            fail_on_low_coverage='true',
            report_format='term'
        )
        self.checker = TestCoverageChecker(self.test_args)
        
    def test_init_with_valid_args(self):
        """Test initialization with valid arguments."""
        self.assertEqual(self.checker.minimum_coverage, 80.0)
        self.assertEqual(self.checker.test_paths, ['tests/', '**/test_*.py'])
        self.assertEqual(self.checker.source_paths, ['.'])
        self.assertEqual(self.checker.exclude_paths, ['tests/', 'setup.py'])
        self.assertTrue(self.checker.fail_on_low_coverage)
        self.assertEqual(self.checker.report_format, 'term')
        
    def test_init_with_false_fail_on_low_coverage(self):
        """Test initialization with fail_on_low_coverage set to false."""
        args = Namespace(
            minimum_coverage='70',
            test_paths='test/',
            source_paths='src/',
            exclude_paths='',
            fail_on_low_coverage='false',
            report_format='html'
        )
        checker = TestCoverageChecker(args)
        
        self.assertEqual(checker.minimum_coverage, 70.0)
        self.assertFalse(checker.fail_on_low_coverage)
        self.assertEqual(checker.report_format, 'html')
        
    def test_init_handles_empty_paths(self):
        """Test initialization handles empty path strings correctly."""
        args = Namespace(
            minimum_coverage='90',
            test_paths='tests/, , **/test_*.py,',  # Empty spaces and trailing comma
            source_paths='., ,src/',  # Empty space
            exclude_paths='',  # Empty string
            fail_on_low_coverage='true',
            report_format='json'
        )
        checker = TestCoverageChecker(args)
        
        # Should filter out empty strings
        self.assertEqual(checker.test_paths, ['tests/', '**/test_*.py'])
        self.assertEqual(checker.source_paths, ['.', 'src/'])
        self.assertEqual(checker.exclude_paths, [])


class TestFileDiscovery(unittest.TestCase):
    """Test file discovery methods."""
    
    def setUp(self):
        """Set up test fixtures with a temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create test file structure
        os.makedirs('tests', exist_ok=True)
        os.makedirs('src', exist_ok=True)
        os.makedirs('other', exist_ok=True)
        
        # Create test files
        open('tests/test_example.py', 'w').close()
        open('tests/test_helper.py', 'w').close()
        open('src/example_test.py', 'w').close()
        open('other/tests.py', 'w').close()
        open('not_a_test.py', 'w').close()
        
        self.test_args = Namespace(
            minimum_coverage='80',
            test_paths='tests/,**/test_*.py,**/tests.py',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        self.checker = TestCoverageChecker(self.test_args)
        
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
        
    def test_find_test_files_with_directory(self):
        """Test finding test files in a directory."""
        test_files = self.checker.find_test_files()
        
        # Should find test files in tests/ directory and matching patterns
        expected_files = {
            'tests/test_example.py',
            'tests/test_helper.py',
            'src/example_test.py',
            'other/tests.py'
        }
        
        found_files = {os.path.relpath(f, self.test_dir) for f in test_files}
        self.assertEqual(found_files, expected_files)
        
    def test_find_test_files_with_glob_pattern(self):
        """Test finding test files using glob patterns."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='**/test_*.py',  # Only glob pattern
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = TestCoverageChecker(args)
        
        test_files = checker.find_test_files()
        found_files = {os.path.relpath(f, self.test_dir) for f in test_files}
        
        expected_files = {
            'tests/test_example.py',
            'tests/test_helper.py'
        }
        self.assertEqual(found_files, expected_files)
        
    def test_find_test_files_no_matches(self):
        """Test behavior when no test files are found."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='nonexistent/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = TestCoverageChecker(args)
        
        test_files = checker.find_test_files()
        self.assertEqual(test_files, [])
        
    def test_find_test_files_specific_file(self):
        """Test finding a specific test file."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/test_example.py',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = TestCoverageChecker(args)
        
        test_files = checker.find_test_files()
        self.assertEqual(len(test_files), 1)
        self.assertTrue(test_files[0].endswith('tests/test_example.py'))


class TestCoverageCommands(unittest.TestCase):
    """Test coverage command building."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='src/',
            exclude_paths='tests/,setup.py',
            fail_on_low_coverage='true',
            report_format='term'
        )
        self.checker = TestCoverageChecker(self.test_args)
        
    def test_build_coverage_command_with_test_files(self):
        """Test building coverage command when test files are provided."""
        test_files = ['tests/test_example.py', 'tests/test_helper.py']
        cmd = self.checker.build_coverage_command(test_files)
        
        expected_parts = [
            'coverage', 'run',
            '--source=src/',
            '--omit', 'tests/',
            '--omit', 'setup.py',
            '-m', 'pytest',
            'tests/test_example.py',
            'tests/test_helper.py'
        ]
        
        self.assertEqual(cmd, expected_parts)
        
    def test_build_coverage_command_no_test_files(self):
        """Test building coverage command when no test files are provided."""
        test_files = []
        cmd = self.checker.build_coverage_command(test_files)
        
        expected_parts = [
            'coverage', 'run',
            '--source=src/',
            '--omit', 'tests/',
            '--omit', 'setup.py',
            '-m', 'unittest', 'discover'
        ]
        
        self.assertEqual(cmd, expected_parts)
        
    def test_build_coverage_command_current_directory_source(self):
        """Test building coverage command with current directory as source."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = TestCoverageChecker(args)
        
        test_files = ['tests/test_example.py']
        cmd = checker.build_coverage_command(test_files)
        
        self.assertIn('--source=.', cmd)


class TestCoverageReporting(unittest.TestCase):
    """Test coverage report generation."""
    
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
        self.checker = TestCoverageChecker(self.test_args)
        
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('builtins.open', mock_open(read_data='{"totals": {"percent_covered": 85.5}}'))
    def test_generate_coverage_report_success(self, mock_exists, mock_subprocess):
        """Test successful coverage report generation."""
        mock_exists.return_value = True
        mock_subprocess.return_value = Mock(stdout="Coverage report", stderr="")
        
        coverage_percentage, report_output = self.checker.generate_coverage_report()
        
        self.assertEqual(coverage_percentage, 85.5)
        self.assertEqual(report_output, "Coverage report")
        
    @patch('subprocess.run')
    def test_generate_coverage_report_json_error(self, mock_subprocess):
        """Test coverage report generation when JSON generation fails."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'coverage')
        
        coverage_percentage, report_output = self.checker.generate_coverage_report()
        
        self.assertEqual(coverage_percentage, 0.0)
        self.assertEqual(report_output, "")
        
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_generate_coverage_report_missing_file(self, mock_exists, mock_subprocess):
        """Test coverage report generation when JSON file is missing."""
        mock_exists.return_value = False
        mock_subprocess.return_value = Mock()
        
        coverage_percentage, report_output = self.checker.generate_coverage_report()
        
        self.assertEqual(coverage_percentage, 0.0)
        self.assertEqual(report_output, "")
        
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('builtins.open', mock_open(read_data='invalid json'))
    def test_generate_coverage_report_invalid_json(self, mock_exists, mock_subprocess):
        """Test coverage report generation with invalid JSON."""
        mock_exists.return_value = True
        mock_subprocess.return_value = Mock()
        
        coverage_percentage, report_output = self.checker.generate_coverage_report()
        
        self.assertEqual(coverage_percentage, 0.0)


class TestGitHubOutputs(unittest.TestCase):
    """Test GitHub Actions output handling."""
    
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
        self.checker = TestCoverageChecker(self.test_args)
        
    @patch.dict(os.environ, {'GITHUB_OUTPUT': '/tmp/github_output'})
    @patch('builtins.open', mock_open())
    def test_set_github_outputs_terminal(self):
        """Test setting GitHub outputs for terminal format."""
        with patch('builtins.open', mock_open()) as mock_file:
            self.checker.set_github_outputs(85.5, "Coverage report", 5)
            
            mock_file.assert_called_once_with('/tmp/github_output', 'a')
            handle = mock_file()
            
            expected_calls = [
                unittest.mock.call.write('coverage_percentage=85.50\n'),
                unittest.mock.call.write('tests_found=5\n'),
                unittest.mock.call.write('coverage_report=terminal_output\n')
            ]
            
            handle.write.assert_has_calls(expected_calls)
            
    @patch.dict(os.environ, {'GITHUB_OUTPUT': '/tmp/github_output'})
    @patch('builtins.open', mock_open())
    def test_set_github_outputs_html(self):
        """Test setting GitHub outputs for HTML format."""
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='html'
        )
        checker = TestCoverageChecker(args)
        
        with patch('builtins.open', mock_open()) as mock_file:
            checker.set_github_outputs(90.0, "HTML report", 3)
            
            handle = mock_file()
            handle.write.assert_any_call('coverage_report=htmlcov/index.html\n')
            
    def test_set_github_outputs_no_env(self):
        """Test setting GitHub outputs when GITHUB_OUTPUT is not set."""
        # Should not raise an exception
        self.checker.set_github_outputs(75.0, "Report", 2)


class TestMainWorkflow(unittest.TestCase):
    """Test the main workflow and integration."""
    
    @patch('TestChecker.TestCoverageChecker.find_test_files')
    @patch('TestChecker.TestCoverageChecker.set_github_outputs')
    def test_run_no_test_files_fail_on_low_coverage(self, mock_set_outputs, mock_find_files):
        """Test run method when no test files found and fail_on_low_coverage is True."""
        mock_find_files.return_value = []
        
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = TestCoverageChecker(args)
        
        exit_code = checker.run()
        
        self.assertEqual(exit_code, 1)
        mock_set_outputs.assert_called_once_with(0.0, "No tests found", 0)
        
    @patch('TestChecker.TestCoverageChecker.find_test_files')
    @patch('TestChecker.TestCoverageChecker.set_github_outputs')
    def test_run_no_test_files_continue_on_low_coverage(self, mock_set_outputs, mock_find_files):
        """Test run method when no test files found and fail_on_low_coverage is False."""
        mock_find_files.return_value = []
        
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='false',
            report_format='term'
        )
        checker = TestCoverageChecker(args)
        
        exit_code = checker.run()
        
        self.assertEqual(exit_code, 0)
        mock_set_outputs.assert_called_once_with(0.0, "No tests found", 0)
        
    @patch('TestChecker.TestCoverageChecker.find_test_files')
    @patch('TestChecker.TestCoverageChecker.run_tests_with_coverage')
    @patch('TestChecker.TestCoverageChecker.generate_coverage_report')
    @patch('TestChecker.TestCoverageChecker.set_github_outputs')
    def test_run_successful_coverage(self, mock_set_outputs, mock_generate_report, 
                                   mock_run_tests, mock_find_files):
        """Test successful run with coverage above threshold."""
        mock_find_files.return_value = ['test_example.py']
        mock_run_tests.return_value = (True, "Tests passed")
        mock_generate_report.return_value = (85.0, "Coverage report")
        
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = TestCoverageChecker(args)
        
        exit_code = checker.run()
        
        self.assertEqual(exit_code, 0)
        mock_set_outputs.assert_called_once_with(85.0, "Coverage report", 1)
        
    @patch('TestChecker.TestCoverageChecker.find_test_files')
    @patch('TestChecker.TestCoverageChecker.run_tests_with_coverage')
    @patch('TestChecker.TestCoverageChecker.generate_coverage_report')
    @patch('TestChecker.TestCoverageChecker.set_github_outputs')
    def test_run_low_coverage_fail(self, mock_set_outputs, mock_generate_report, 
                                 mock_run_tests, mock_find_files):
        """Test run with coverage below threshold and fail_on_low_coverage=True."""
        mock_find_files.return_value = ['test_example.py']
        mock_run_tests.return_value = (True, "Tests passed")
        mock_generate_report.return_value = (60.0, "Coverage report")
        
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = TestCoverageChecker(args)
        
        exit_code = checker.run()
        
        self.assertEqual(exit_code, 1)
        
    @patch('TestChecker.TestCoverageChecker.find_test_files')
    @patch('TestChecker.TestCoverageChecker.run_tests_with_coverage')
    def test_run_test_execution_failure(self, mock_run_tests, mock_find_files):
        """Test run when test execution fails."""
        mock_find_files.return_value = ['test_example.py']
        mock_run_tests.return_value = (False, "Test execution failed")
        
        args = Namespace(
            minimum_coverage='80',
            test_paths='tests/',
            source_paths='.',
            exclude_paths='',
            fail_on_low_coverage='true',
            report_format='term'
        )
        checker = TestCoverageChecker(args)
        
        exit_code = checker.run()
        
        self.assertEqual(exit_code, 1)


class TestMainFunction(unittest.TestCase):
    """Test the main function and argument parsing."""
    
    @patch('sys.argv', ['TestChecker.py', '--minimum-coverage', '90'])
    @patch('TestChecker.TestCoverageChecker.run')
    def test_main_with_custom_coverage(self, mock_run):
        """Test main function with custom minimum coverage."""
        mock_run.return_value = 0
        
        exit_code = main()
        
        self.assertEqual(exit_code, 0)
        mock_run.assert_called_once()
        
    @patch('sys.argv', ['TestChecker.py'])
    @patch('TestChecker.TestCoverageChecker.run')
    def test_main_with_defaults(self, mock_run):
        """Test main function with default arguments."""
        mock_run.return_value = 0
        
        exit_code = main()
        
        self.assertEqual(exit_code, 0)
        mock_run.assert_called_once()


if __name__ == '__main__':
    # Set up test discovery and run tests
    unittest.main(verbosity=2) 