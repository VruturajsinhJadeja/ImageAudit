import os
import io
import requests
import pandas as pd
import concurrent.futures
from datetime import datetime
from PIL import Image, UnidentifiedImageError

import config

class SupersetValidator:
    def __init__(self):
        self.session = requests.Session()

    def login(self):
        print("🔐 Authenticating...")
        try:
            # 1. Login
            login_url = f"{config.SUPERSET_URL}/api/v1/security/login"
            payload = {"username": config.USERNAME, "password": config.PASSWORD, "provider": "db", "refresh": True}
            res = self.session.post(login_url, json=payload)
            res.raise_for_status()
            token = res.json().get('access_token')
            self.session.headers.update({'Authorization': f'Bearer {token}'})

            # 2. Get CSRF
            csrf_url = f"{config.SUPERSET_URL}/api/v1/security/csrf_token/"
            res = self.session.get(csrf_url)
            res.raise_for_status()
            csrf = res.json().get('result')
            self.session.headers.update({'X-CSRF-Token': csrf})
            
            print("   ✅ Login successful.")
            return True
        except Exception as e:
            print(f"   ❌ Login failed: {e}")
            return False

    def fetch_data(self):
        print(f"📥 Fetching records from DB {config.DB_ID}...")
        try:
            url = f"{config.SUPERSET_URL}/api/v1/sqllab/execute/"
            payload = {
                "database_id": config.DB_ID,
                "sql": config.SQL_QUERY,
                "schema": config.DB_SCHEMA,
                "runAsync": False,
                "queryLimit": 10000
            }
            res = self.session.post(url, json=payload)
            res.raise_for_status()
            data = res.json().get('data', [])
            return pd.DataFrame(data)
        except Exception as e:
            print(f"   ❌ Query failed: {e}")
            return pd.DataFrame()

    def _validate_single_url(self, url):
        """
        Helper function to validate one URL.
        Returns: (status_str, size_float, dimensions_str)
        """
        if not url:
            return "FAIL: Empty/Null", 0, "N/A"

        try:
            # 1. Download
            response = requests.get(url, timeout=config.TIMEOUT_SECONDS)
            if response.status_code != 200:
                return f"FAIL: HTTP {response.status_code}", 0, "N/A"

            # 2. Measure Size
            size_bytes = len(response.content)
            size_kb = round(size_bytes / 1024, 2)
            
            # 3. Measure Dimensions
            try:
                img = Image.open(io.BytesIO(response.content))
                width, height = img.size
                dims_str = f"{width}x{height}"
            except UnidentifiedImageError:
                return "FAIL: Not an Image", size_kb, "N/A"

            # 4. Detailed Validation Logic
            violations = []

            # --- Check Size ---
            if config.CHECK_SIZE:
                if size_kb < config.MIN_SIZE_KB:
                    violations.append(f"Size < {config.MIN_SIZE_KB}KB")
                elif size_kb > config.MAX_SIZE_KB:
                    violations.append(f"Size > {config.MAX_SIZE_KB}KB")

            # --- Check Exact Dimensions ---
            if config.CHECK_DIMS:
                if config.EXPECTED_WIDTH and width != config.EXPECTED_WIDTH:
                    violations.append(f"Invalid Width (Expected {config.EXPECTED_WIDTH}px)")
                
                if config.EXPECTED_HEIGHT and height != config.EXPECTED_HEIGHT:
                    violations.append(f"Invalid Height (Expected {config.EXPECTED_HEIGHT}px)")

            # 5. Determine Status
            if not violations:
                return "PASS", size_kb, dims_str
            else:
                return "FAIL: " + ", ".join(violations), size_kb, dims_str

        except Exception as e:
            return f"FAIL: Error {str(e)[:20]}", 0, "N/A"

    def process_row(self, row):
        sku = row.get(config.COL_ID)
        
        # Initialize result row with just the SKU
        result_row = {"sku_code": sku}

        # Iterate through every image column defined in config
        for col_name in config.IMAGE_COLUMNS:
            url = row.get(col_name)
            
            # Perform validation
            status, size, dims = self._validate_single_url(url)
            
            # Assign to separate columns
            result_row[f"{col_name}_status"] = status
            result_row[f"{col_name}_size_kb"] = size
            result_row[f"{col_name}_dimensions"] = dims
            result_row[f"{col_name}_url"] = url  

        return result_row

    def run(self):
        if not self.login(): return
        df = self.fetch_data()
        
        if df.empty:
            print("   ⚠️ No data found.")
            return

        print(f"🚀 Processing {len(df)} records (Checking {len(config.IMAGE_COLUMNS)} columns per record)...")
        results_list = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_THREADS) as executor:
            rows = df.to_dict('records')
            processed_rows = executor.map(self.process_row, rows)
            
            for i, res in enumerate(processed_rows):
                results_list.append(res)
                if (i + 1) % 10 == 0:
                    print(f"   Processed {i+1}/{len(df)}...", end='\r')

        print(f"\n✅ Processing complete.")
        self.save_report_with_formatting(results_list)

    def save_report_with_formatting(self, data):
        if not os.path.exists(config.OUTPUT_FOLDER):
            os.makedirs(config.OUTPUT_FOLDER)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{config.OUTPUT_FOLDER}/Audit_Report_{timestamp}.xlsx"
        
        df = pd.DataFrame(data)

        # 1. Organize Columns order
        ordered_cols = ["sku_code"]
        for col_name in config.IMAGE_COLUMNS:
            ordered_cols.append(f"{col_name}_status")
            ordered_cols.append(f"{col_name}_size_kb")
            ordered_cols.append(f"{col_name}_dimensions")
            ordered_cols.append(f"{col_name}_url") 
        
        # Filter to ensure column existence and order
        df = df[ordered_cols]

        # 2. Rename Columns for Display
        rename_map = {"sku_code": "SKU Code"}
        for col_name in config.IMAGE_COLUMNS:
            rename_map[f"{col_name}_status"] = f"{col_name} Status"
            rename_map[f"{col_name}_size_kb"] = f"{col_name} Size (in KB)"
            rename_map[f"{col_name}_dimensions"] = f"{col_name} Dimensions (Width x Height)"
            rename_map[f"{col_name}_url"] = f"{col_name} URL" 
        
        df.rename(columns=rename_map, inplace=True)

        # 3. Write to Excel
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            
            # --- Define Formats ---
            # Center alignment for general cells
            center_fmt = workbook.add_format({
                'align': 'center', 
                'valign': 'vcenter',
                'border': 1
            })
            
            # Conditional Formatting: Green
            green_fmt = workbook.add_format({
                'bg_color': '#C6EFCE', 
                'font_color': '#006100',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            
            # Conditional Formatting: Red
            red_fmt = workbook.add_format({
                'bg_color': '#FFC7CE', 
                'font_color': '#9C0006',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })

            # Freeze the top row and first column
            worksheet.freeze_panes(1, 1)

            # Apply formatting to columns
            for col_num, col_name in enumerate(df.columns):
                
                # A. Set Column Widths based on content
                width = 20
                if "Status" in col_name:
                    width = 45 # Increased slightly to accommodate new strict dimension text 
                elif "Size" in col_name:
                    width = 18
                elif "Dimensions" in col_name:
                    width = 30
                elif "URL" in col_name:
                    width = 50  
                
                worksheet.set_column(col_num, col_num, width, center_fmt)

                # B. Apply Conditional Formatting only to "Status" columns
                if "Status" in col_name:
                    start_row = 1
                    end_row = len(df) + 1
                    
                    # Green for PASS
                    worksheet.conditional_format(start_row, col_num, end_row, col_num, {
                        'type':     'cell',
                        'criteria': '==',
                        'value':    '"PASS"',
                        'format':   green_fmt
                    })
                    
                    # Red for FAIL (includes Empty/Null)
                    worksheet.conditional_format(start_row, col_num, end_row, col_num, {
                        'type':     'text',
                        'criteria': 'containing',
                        'value':    'FAIL',
                        'format':   red_fmt
                    })

        print(f"📄 Report generated: {filename}")

if __name__ == "__main__":
    validator = SupersetValidator()
    validator.run()