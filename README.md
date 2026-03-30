# Superset Image Validator

## Overview
This tool is a Python-based automation script designed to validate images stored in a Superset-connected database. It fetches image URLs via the Superset SQL Lab API, downloads them in parallel, and checks them against defined quality standards (file size and dimensions).

The final output is a color-coded Excel report indicating which images passed or failed validation.

## Features
- **Superset Integration**: Authenticates via API (Login + CSRF Token) and runs custom SQL queries.
- **Performance**: Uses Multi-threading (`concurrent.futures`) to process multiple images simultaneously.
- **Validation Rules**:
  - Checks for broken links (HTTP 404/500).
  - Validates File Size (Min/Max KB).
  - Validates Image Dimensions (Width/Height pixels).
- **Reporting**: Generates an Excel file with Conditional Formatting:
  - 🟢 **Green**: PASS
  - 🔴 **Red**: FAIL (with specific error details)

## Project Structure
```text
project_root/
├── config.py           # Configuration (Credentials, Thresholds, SQL)
├── validator.py        # Main execution script
├── requirements.txt    # Python dependencies
├── README.md           # Documentation
└── reports/            # Generated Excel reports appear here

