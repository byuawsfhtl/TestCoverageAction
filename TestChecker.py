#!/usr/bin/env python3
"""
Test Coverage Checker for GitHub Actions
Scans repository for tests, calculates coverage, and reports results.
"""

import argparse
import os
import sys
import subprocess
import glob
import json
from typing import List, Tuple


class CoverageChecker:
    """Main class for test coverage checking functionality."""
    
    def __init__(self, args: argparse.Namespace) -> None:
        """
        Initialize the CoverageChecker class.

        Args:
            args: argparse.Namespace object containing command line arguments

        Returns:
            None
        """
        self.minimum_coverage = float(args.minimum_coverage)
        self.test_paths = [p.strip() for p in args.test_paths.split(',') if p.strip()]
        self.source_paths = [p.strip() for p in args.source_paths.split(',') if p.strip()]
        self.exclude_paths = [p.strip() for p in args.exclude_paths.split(',') if p.strip()]
        self.fail_on_low_coverage = args.fail_on_low_coverage.lower() == 'true'
        self.report_format = args.report_format
        self.workspace_path = os.getcwd()
        
    def find_test_files(self) -> list[str]:
        """
        Discover test files in the repository.

        Args:
            None

        Returns:
            List[str]: List of test files found in the repository
        """
        test_files = []
        
        print("Discovering test files...")
        
        for test_path in self.test_paths:
            # Handle glob patterns
            if '*' in test_path:
                matches = glob.glob(test_path, recursive=True)
                test_files.extend(matches)
            else:
                self._handle_file_paths(test_path, test_files)
        
        # Remove duplicates and non-existent files
        test_files = list(set([f for f in test_files if os.path.isfile(f)]))
        
        # Convert to relative paths for display
        relative_paths = [os.path.relpath(f, self.workspace_path).replace(os.sep, '/') for f in test_files]
        
        print(f"Found {len(test_files)} test files:")
        for relative_path in relative_paths:
            print(f"   • {relative_path}")
            
        return test_files
    
    def _handle_file_paths(self, test_path: str, test_files: list[str]) -> None:
        """
        Handle file paths for test discovery.

        Args:
            test_path: str, the path to the test file or directory
            test_files: List[str], the list of test files found so far

        Returns:
            None
        """
        full_path = os.path.join(self.workspace_path, test_path)
        if os.path.isdir(full_path):
            self._find_tests_in_dir(full_path, test_files)
        elif os.path.isfile(full_path) and full_path.endswith('.py'):
            test_files.append(full_path)

    def _find_tests_in_dir(self, full_path: str, test_files: list[str]) -> None:
        """
        Find tests in a directory.

        Args:
            full_path: str, the path to the directory to search
            test_files: List[str], the list of test files found so far

        Returns:
            None
        """
        for root, _, files in os.walk(full_path):
            for file in files:
                if (file.startswith('test_') and file.endswith('.py')) or \
                    (file.endswith('_test.py')) or \
                    (file == 'tests.py'):
                    test_files.append(os.path.join(root, file))
    
    def build_coverage_command(self, test_files: list[str]) -> list[str]:
        """
        Build the coverage command to run tests with coverage collection.

        Args:
            test_files: List[str], the list of test files to run

        Returns:
            List[str]: The coverage command to run tests with coverage collection
        """
        # Create source include pattern
        source_include = []
        for source_path in self.source_paths:
            if source_path == '.':
                source_include.append('--source=.')
            else:
                source_include.append(f'--source={source_path}')
        
        # Create exclude pattern
        exclude_patterns = []
        for exclude_path in self.exclude_paths:
            exclude_patterns.extend(['--omit', exclude_path])
        
        # Build the command
        cmd = ['coverage', 'run'] + source_include + exclude_patterns
        
        # Add pytest runner if test files found, otherwise use unittest discovery
        if test_files:
            cmd.extend(['-m', 'pytest'] + test_files)
        else:
            cmd.extend(['-m', 'unittest', 'discover'])
            
        return cmd
    
    def run_tests_with_coverage(self, test_files: list[str]) -> tuple[bool, str]:
        """
        Run tests with coverage collection.

        Args:
            test_files: List[str], the list of test files to run

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating success and a string containing the test output
        """
        print("\nRunning tests with coverage...")
        
        # Build and run coverage command
        cmd = self.build_coverage_command(test_files)
        print(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.workspace_path
            )
            
            print("Test output:")
            print(result.stdout)
            if result.stderr:
                print("Errors:")
                print(result.stderr)
            
            # Check if tests passed (return code 0 means success)
            if result.returncode != 0:
                print(f"Error: Tests failed with return code {result.returncode}")
                return False, result.stdout + result.stderr
                
            print("Success: All tests passed!")
            return True, result.stdout + result.stderr
            
        except subprocess.CalledProcessError as e:
            print(f"Error: Error running tests: {e}")
            return False, f"Error running tests: {str(e)}"
        except FileNotFoundError:
            print("Error: Coverage tool not found. Make sure 'coverage' is installed.")
            return False, "Coverage tool not found"
    
    def generate_coverage_report(self) -> tuple[float, str]:
        """
        Generate and parse coverage report.

        Args:
            None

        Returns:
            Tuple[float, str]: A tuple containing the coverage percentage and the coverage report
        """
        print("\nGenerating coverage report...")
        
        # Generate JSON report for parsing
        json_cmd = ['coverage', 'json', '-o', 'coverage.json']
        try:
            subprocess.run(json_cmd, check=True, cwd=self.workspace_path)
        except subprocess.CalledProcessError as e:
            print(f"Error: Error generating JSON report: {e}")
            return 0.0, ""
        
        # Parse JSON report
        coverage_file = os.path.join(self.workspace_path, 'coverage.json')
        if not os.path.exists(coverage_file):
            print("Error: Coverage JSON file not found")
            return 0.0, ""
            
        try:
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
            
            total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0.0)
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error: Error parsing coverage JSON: {e}")
            return 0.0, ""
        
        # Generate human-readable report
        report_cmd = ['coverage', 'report']
        if self.report_format == 'html':
            report_cmd = ['coverage', 'html', '-d', 'htmlcov']
        elif self.report_format == 'xml':
            report_cmd = ['coverage', 'xml', '-o', 'coverage.xml']
        
        try:
            result = subprocess.run(
                report_cmd,
                capture_output=True,
                text=True,
                cwd=self.workspace_path
            )
            report_output = result.stdout
        except subprocess.CalledProcessError:
            report_output = "Could not generate detailed report"
        
        return total_coverage, report_output
    
    def set_github_outputs(self, coverage_percentage: float, tests_found: int) -> None:
        """
        Set GitHub Action outputs.

        Args:
            coverage_percentage: float, the coverage percentage
            tests_found: int, the number of tests found

        Returns:
            None
        """
        github_output = os.environ.get('GITHUB_OUTPUT')
        if github_output:
            try:
                with open(github_output, 'a') as f:
                    f.write(f"coverage_percentage={coverage_percentage:.2f}\n")
                    f.write(f"tests_found={tests_found}\n")
                    
                    # Set report file path based on format
                    if self.report_format == 'html':
                        f.write(f"coverage_report=htmlcov/index.html\n")
                    elif self.report_format == 'xml':
                        f.write(f"coverage_report=coverage.xml\n")
                    elif self.report_format == 'json':
                        f.write(f"coverage_report=coverage.json\n")
                    else:
                        f.write(f"coverage_report=terminal_output\n")
                        
                print("Success: GitHub Action outputs set")
            except Exception as e:
                print(f"Error: Could not set GitHub outputs: {e}")
    
    def run(self) -> int:
        """
        Main execution method.

        Args:
            None

        Returns:
            int: The exit code
        """
        print("Starting Test Coverage Check...")
        print(f"   Minimum coverage required: {self.minimum_coverage}%")
        print(f"   Test paths: {', '.join(self.test_paths)}")
        print(f"   Source paths: {', '.join(self.source_paths)}")
        print(f"   Exclude paths: {', '.join(self.exclude_paths)}")
        print(f"   Report format: {self.report_format}")
        
        # Step 1: Find test files
        test_files = self.find_test_files()
        
        if not test_files:
            print("Warning: No test files found!")
            self.set_github_outputs(0.0, 0)
            if self.fail_on_low_coverage:
                return 1
            return 0
        
        # Step 2: Run tests with coverage
        success, test_output = self.run_tests_with_coverage(test_files)
        if not success:
            print("Error: Tests failed or could not be run")
            self.set_github_outputs(0.0, len(test_files))
            return 1
        
        # Step 3: Generate coverage report
        coverage_percentage, report_output = self.generate_coverage_report()
        
        # Step 4: Display results
        print(f"\nCoverage Results:")
        print(f"   Total Coverage: {coverage_percentage:.2f}%")
        print(f"   Required Coverage: {self.minimum_coverage}%")
        print(f"\n{report_output}")
        
        # Step 5: Set GitHub outputs
        self.set_github_outputs(coverage_percentage, len(test_files))
        
        # Step 6: Check if coverage meets requirements
        if coverage_percentage < self.minimum_coverage:
            print(f"Error: Coverage {coverage_percentage:.2f}% is below required {self.minimum_coverage}%")
            if self.fail_on_low_coverage:
                return 1
            else:
                print("Warning: Continuing despite low coverage (fail_on_low_coverage=false)")
        else:
            print(f"Success: Coverage {coverage_percentage:.2f}% meets requirement of {self.minimum_coverage}%")
        
        return 0


def main() -> int:
    """
    Main entry point.

    Args:
        None

    Returns:
        int: The exit code
    """
    parser = argparse.ArgumentParser(description='Test Coverage Checker for GitHub Actions')
    
    parser.add_argument('--minimum-coverage', 
        default='80', 
        help='Minimum coverage percentage required (0-100)')
    parser.add_argument('--test-paths', 
        default='tests/,test/,**/test_*.py,**/tests.py', 
        help='Comma-separated list of test directories/files to include')
    parser.add_argument('--source-paths', 
        default='.', 
        help='Comma-separated list of source directories to analyze')
    parser.add_argument('--exclude-paths',  
        default='tests/,test/,**/test_*.py,**/tests.py,setup.py,conftest.py',
        help='Comma-separated list of paths to exclude from coverage')
    parser.add_argument('--fail-on-low-coverage', 
        default='true',
        help='Whether to fail the action if coverage is below minimum')
    parser.add_argument('--report-format', 
        default='term',
        choices=['term', 'html', 'xml', 'json'],
        help='Coverage report format')
    
    args = parser.parse_args()
    
    checker = CoverageChecker(args)
    exit_code = checker.run()
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
