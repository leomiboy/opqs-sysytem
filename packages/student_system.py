import pandas as pd
import streamlit as st
from datetime import datetime
from packages.auth import get_google_services

class StudentSystem:
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.sheets_service, _ = get_google_services()
        
    def _create_sheet_if_not_exists(self, title, headers):
        """
        Helper to create a sheet with headers if it doesn't exist.
        """
        if not self.sheets_service:
            return

        try:
            # Check if sheet exists
            spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            sheet_titles = [s['properties']['title'] for s in sheets]
            
            if title not in sheet_titles:
                # Create sheet
                batch_update_request = {
                    'requests': [
                        {
                            'addSheet': {
                                'properties': {'title': title}
                            }
                        }
                    ]
                }
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id, 
                    body=batch_update_request
                ).execute()
                
                # Write headers
                self._append_row(title, headers)
                st.toast(f"已建立資料表: {title}")
                
        except Exception as e:
            st.error(f"Error creating sheet {title}: {e}")

    def _append_row(self, sheet_name, values):
        """
        Append a row to the specified sheet.
        """
        if not self.sheets_service:
            return False
            
        range_name = f"'{sheet_name}'!A1"
        body = {'values': [values]}
        
        try:
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            return True
        except Exception as e:
            st.error(f"Error writing to {sheet_name}: {e}")
            return False

    def init_schema(self):
        """
        Initialize the database schema for System 1.
        Creates 'Digital_Footprint', 'Students', and 'Modules' sheets if missing.
        """
        # 1. Digital Footprint (Big Table)
        self._create_sheet_if_not_exists(
            "Digital_Footprint", 
            ["Timestamp", "Student_ID", "Question_ID", "Result", "Selected_Option", "Mode", "Module"]
        )
        
        # 2. Students Account
        self._create_sheet_if_not_exists(
            "Students",
            ["Student_ID", "Name", "Class", "Target_Module", "Login_Code"]
        )
        
        # 3. Modules Definition
        self._create_sheet_if_not_exists(
            "Modules",
            ["Module_Name", "Filter_Source", "Filter_Year", "Filter_Unit", "Filter_Diff", "Count_Easy", "Count_Mid", "Count_Hard"]
        )
        
        # 4. Active Sessions (For Persistence)
        self._create_sheet_if_not_exists(
            "Active_Sessions",
            ["Student_ID", "Question_UIDs", "Mode", "Module", "Start_Time", "Current_Index"]
        )

    # ... (login method remains same) ...

    # ... (log_footprint method remains same) ...
    
    # ... (import_students method remains same) ...

    def save_module(self, module_data):
        """
        Save a new module configuration to 'Modules' sheet.
        module_data: list matching headers
        """
        if not self.sheets_service:
            return False
        
        # Check if module name exists (Optional, for now just append)
        # Better: Read all and check uniqueness? 
        # For simplicity in V1, just append. User can manage duplicate names by picking latest or unique naming.
        
        return self._append_row("Modules", module_data)
        
    def get_module(self, module_name):
        """
        Retrieve module config by name.
        Returns dict or None.
        """
        if not self.sheets_service:
            return None
            
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, 
                range="'Modules'!A:H"
            ).execute()
            values = result.get('values', [])
            
            if not values or len(values) < 2:
                return None
            
            headers = values[0] # Module_Name, ...
            # Find row
            # Assuming Module_Name is col 0
            for row in values[1:]:
                if row[0] == module_name:
                    # Pad row if incomplete
                    if len(row) < len(headers):
                        row += [""] * (len(headers) - len(row))
                    return dict(zip(headers, row))
            
            return None
        except Exception as e:
            st.error(f"Get module failed: {e}")
            return None
            
    def get_all_modules_list(self):
        """
        Get list of all available module names.
        """
        if not self.sheets_service:
            return []
            
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, 
                range="'Modules'!A2:A"
            ).execute()
            values = result.get('values', [])
            return [row[0] for row in values if row]
        except:
            return []

    def save_session(self, student_id, q_uids, mode, module, current_index=0):
        """
        Save or Update active session.
        Auto-creates Active_Sessions sheet if it doesn't exist.
        """
        if not self.sheets_service: return False
        
        # Ensure sheet exists (idempotent, no-op if already there)
        self._create_sheet_if_not_exists(
            "Active_Sessions",
            ["Student_ID", "Question_UIDs", "Mode", "Module", "Start_Time", "Current_Index"]
        )
        
        # Delete existing first (Simulate Update)
        self.delete_session(student_id)
        
        row = [
            str(student_id),
            ",".join(q_uids),
            mode,
            module,
            datetime.now().isoformat(),
            str(current_index)
        ]
        return self._append_row("Active_Sessions", row)

    def get_active_session(self, student_id):
        """
        Get active session for student.
        """
        if not self.sheets_service: return None
        
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="'Active_Sessions'!A:F"
            ).execute()
            values = result.get('values', [])
            
            if not values or len(values) < 2: return None
            
            headers = values[0]
            for row in values[1:]:
                if row[0] == str(student_id):
                    # Pad headers if needed
                    while len(row) < len(headers):
                        row.append("")
                    return dict(zip(headers, row))
            return None
        except Exception as e:
            print(f"Error getting session: {e}")
            return None

    def delete_session(self, student_id):
        """
        Remove session for student. 
        """
        if not self.sheets_service: return False
        
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="'Active_Sessions'!A:F"
            ).execute()
            values = result.get('values', [])
            
            if not values: return True
            
            new_values = [values[0]] # Header
            found = False
            for row in values[1:]:
                # Check for empty rows
                if not row: continue
                if row[0] != str(student_id):
                    new_values.append(row)
                else:
                    found = True
            
            if found:
                 self.sheets_service.spreadsheets().values().clear(
                    spreadsheetId=self.spreadsheet_id,
                    range="'Active_Sessions'!A:F"
                ).execute()
                
                 body = {'values': new_values}
                 self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range="'Active_Sessions'!A1",
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
            
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False

    def login(self, student_id, login_code=None):
        """
        Verify student login.
        Returns student info dict or None.
        """
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, 
                range="'Students'!A:E"
            ).execute()
            values = result.get('values', [])
            
            if not values or len(values) < 2:
                return None
                
            headers = values[0]
            df = pd.DataFrame(values[1:], columns=headers)
            
            # Simple retrieval
            student = df[df['Student_ID'] == student_id]
            
            if not student.empty:
                # Optionally check login code if implemented
                return student.iloc[0].to_dict()
                
            return None
            
        except Exception as e:
            st.error(f"Login failed: {e}")
            return None

    def log_footprint(self, records):
        """
        Batch log user footprint.
        records: List of lists containing row data.
        """
        if not self.sheets_service or not records:
            return False
            
        range_name = "'Digital_Footprint'!A1"
        body = {'values': records}
        
        try:
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            return True
        except Exception as e:
            st.error(f"Failed to log footprint: {e}")
            return False

    def import_students(self, df):
        """
        Import students from DataFrame to 'Students' sheet.
        Replaces existing data.
        """
        if not self.sheets_service:
            return False
            
        required_cols = ["Student_ID", "Name", "Class", "Target_Module", "Login_Code"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"CSV 格式錯誤！缺少欄位: {required_cols}")
            return False
            
        try:
            # 1. Clear existing data (preserve header row 1)
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range="'Students'!A2:E"
            ).execute()
            
            # 2. Convert to list of lists
            # Fill NaN with empty string
            df = df.fillna("")
            # Ensure order matches required_cols
            values = df[required_cols].astype(str).values.tolist()
            
            if not values:
                return True # Empty but success clearing
            
            # 3. Write new data
            body = {'values': values}
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range="'Students'!A2",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            st.error(f"匯入學生名單失敗: {e}")
            return False
