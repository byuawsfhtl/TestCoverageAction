# Test Coverage Action

A GitHub Action that scans repositories for tests, calculates test coverage, and reports coverage percentage.

## Features

- **🔍 Auto-discovery**: Finds test files using configurable patterns
- **📊 Coverage calculation**: Uses Python's `coverage.py` tool for accurate metrics  
- **⚙️ Flexible configuration**: Customizable coverage thresholds and paths
- **📈 Multiple report formats**: Terminal, HTML, XML, and JSON output
- **🚫 Smart exclusions**: Excludes test files and specified paths from coverage
- **✅ CI integration**: Seamless GitHub Actions workflow integration

## Usage

Add this step to your GitHub Actions workflow:

```yaml
- name: Check Test Coverage
  uses: ./
  with:
    minimum_coverage: '80'           # Required coverage percentage
    test_paths: 'tests/,**/test_*.py' # Where to find tests
    source_paths: '.'                # Source code to analyze
    exclude_paths: 'tests/,setup.py' # Paths to exclude
    fail_on_low_coverage: 'true'     # Fail if below threshold. For older repos that are building coverage, change this to false
    report_format: 'term'            # Report format (term/html/xml/json)
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `minimum_coverage` | Minimum coverage percentage (0-100) | No | `80` |
| `test_paths` | Comma-separated test directories/files | No | `tests/,test/,**/test_*.py,**/tests.py` |
| `source_paths` | Comma-separated source directories | No | `.` |
| `exclude_paths` | Comma-separated paths to exclude | No | `tests/,test/,**/test_*.py,**/tests.py,setup.py,conftest.py` |
| `fail_on_low_coverage` | Fail action if coverage below minimum | No | `true` |
| `report_format` | Coverage report format | No | `term` |

## Outputs

| Output | Description |
|--------|-------------|
| `coverage_percentage` | Calculated test coverage percentage |
| `coverage_report` | Path to generated coverage report |
| `tests_found` | Number of test files discovered |

## Examples

### Basic Usage
```yaml
- name: Test Coverage Check  
  uses: ./
```

### Custom Configuration
```yaml
- name: Test Coverage Check
  uses: ./
  with:
    minimum_coverage: '90'
    test_paths: 'my_tests/,unit_tests/'
    source_paths: 'src/,lib/'
    exclude_paths: 'tests/,migrations/'
    report_format: 'html'
```

### Generate HTML Report
```yaml
- name: Test Coverage Check
  uses: ./
  with:
    report_format: 'html'

- name: Upload Coverage Report
  uses: actions/upload-artifact@v3
  with:
    name: coverage-report
    path: htmlcov/
```

## Development

The action consists of:
- `action.yml` - Action metadata and interface
- `TestChecker.py` - Main coverage checking logic
- `requirements.txt` - Python dependencies
