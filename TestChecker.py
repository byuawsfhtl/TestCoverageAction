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
from pathlib import Path
from typing import List, Tuple, Dict


class TestCoverageChecker:
    """Main class for test coverage checking functionality."""
    
    def __init__(self, args):
        self.minimum_coverage = float(args.minimum_coverage)
        self.test_paths = [p.strip() for p in args.test_paths.split(',') if p.strip()]
        self.source_paths = [p.strip() for p in args.source_paths.split(',') if p.strip()]
        self.exclude_paths = [p.strip() for p in args.exclude_paths.split(',') if p.strip()]
        self.fail_on_low_coverage = args.fail_on_low_coverage.lower() == 'true'
        self.report_format = args.report_format
        self.workspace_path = os.getcwd()
        
    def find_test_files(self) -> List[str]:
        """Discover test files in the repository."""
        test_files = []
        
        print("🔍 Discovering test files...")
        
        for test_path in self.test_paths:
            # Handle glob patterns
            if '*' in test_path:
                matches = glob.glob(test_path, recursive=True)
                test_files.extend(matches)
            else:
                # Handle directory or file paths
                full_path = os.path.join(self.workspace_path, test_path)
                if os.path.isdir(full_path):
                    # Find Python test files in directory
                    for root, dirs, files in os.walk(full_path):
                        for file in files:
                            if (file.startswith('test_') and file.endswith('.py')) or \
                               (file.endswith('_test.py')) or \
                               (file == 'tests.py'):
                                test_files.append(os.path.join(root, file))
                elif os.path.isfile(full_path) and full_path.endswith('.py'):
                    test_files.append(full_path)
        
        # Remove duplicates and non-existent files
        test_files = list(set([f for f in test_files if os.path.isfile(f)]))
        
        print(f"📁 Found {len(test_files)} test files:")
        for test_file in test_files:
            print(f"   • {os.path.relpath(test_file, self.workspace_path)}")
            
        return test_files
    
    def build_coverage_command(self, test_files: List[str]) -> List[str]:
        """Build the coverage command to run tests with coverage collection."""
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
    
    def run_tests_with_coverage(self, test_files: List[str]) -> Tuple[bool, str]:
        """Run tests with coverage collection."""
        print("\n🧪 Running tests with coverage...")
        
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
                
            # Tests can fail but we still want coverage report
            return True, result.stdout + result.stderr
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running tests: {e}")
            return False, str(e)
        except FileNotFoundError:
            print("❌ Coverage tool not found. Make sure 'coverage' is installed.")
            return False, "Coverage tool not found"
    
    def generate_coverage_report(self) -> Tuple[float, str]:
        """Generate and parse coverage report."""
        print("\n📊 Generating coverage report...")
        
        # Generate JSON report for parsing
        json_cmd = ['coverage', 'json', '-o', 'coverage.json']
        try:
            subprocess.run(json_cmd, check=True, cwd=self.workspace_path)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generating JSON report: {e}")
            return 0.0, ""
        
        # Parse JSON report
        coverage_file = os.path.join(self.workspace_path, 'coverage.json')
        if not os.path.exists(coverage_file):
            print("❌ Coverage JSON file not found")
            return 0.0, ""
            
        try:
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
            
            total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0.0)
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error parsing coverage JSON: {e}")
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
    
    def set_github_outputs(self, coverage_percentage: float, report_output: str, tests_found: int):
        """Set GitHub Action outputs."""
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
                        
                print("✅ GitHub Action outputs set")
            except Exception as e:
                print(f"⚠️  Could not set GitHub outputs: {e}")
    
    def run(self) -> int:
        """Main execution method."""
        print("🚀 Starting Test Coverage Check")
        print(f"   Minimum coverage required: {self.minimum_coverage}%")
        print(f"   Test paths: {', '.join(self.test_paths)}")
        print(f"   Source paths: {', '.join(self.source_paths)}")
        print(f"   Exclude paths: {', '.join(self.exclude_paths)}")
        print(f"   Report format: {self.report_format}")
        
        # Step 1: Find test files
        test_files = self.find_test_files()
        
        if not test_files:
            print("⚠️  No test files found!")
            self.set_github_outputs(0.0, "No tests found", 0)
            if self.fail_on_low_coverage:
                return 1
            return 0
        
        # Step 2: Run tests with coverage
        success, test_output = self.run_tests_with_coverage(test_files)
        if not success:
            print("❌ Failed to run tests")
            self.set_github_outputs(0.0, test_output, len(test_files))
            return 1
        
        # Step 3: Generate coverage report
        coverage_percentage, report_output = self.generate_coverage_report()
        
        # Step 4: Display results
        print(f"\n📈 Coverage Results:")
        print(f"   Total Coverage: {coverage_percentage:.2f}%")
        print(f"   Required Coverage: {self.minimum_coverage}%")
        print(f"\n{report_output}")
        
        # Step 5: Set GitHub outputs
        self.set_github_outputs(coverage_percentage, report_output, len(test_files))
        
        # Step 6: Check if coverage meets requirements
        if coverage_percentage < self.minimum_coverage:
            print(f"❌ Coverage {coverage_percentage:.2f}% is below required {self.minimum_coverage}%")
            if self.fail_on_low_coverage:
                return 1
            else:
                print("⚠️  Continuing despite low coverage (fail_on_low_coverage=false)")
        else:
            print(f"✅ Coverage {coverage_percentage:.2f}% meets requirement of {self.minimum_coverage}%")
        
        return 0


def main():
    """Main entry point."""
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
    
    checker = TestCoverageChecker(args)
    exit_code = checker.run()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
