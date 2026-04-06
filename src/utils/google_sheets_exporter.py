"""
Google Sheets Export Utility
Exports lead data to Google Sheets for easy sharing
"""

import pandas as pd
from typing import Optional
import csv
from io import StringIO


class GoogleSheetsExporter:
    """
    Export data in Google Sheets compatible format
    """
    
    def prepare_for_sheets(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare DataFrame for Google Sheets upload
        
        Args:
            df: Input DataFrame
            
        Returns:
            Formatted DataFrame
        """
        # Select columns for export
        export_columns = [
            'rank', 'propensity_score', 'name', 'title', 'company',
            'location', 'company_hq', 'email', 'linkedin',
            'recent_publication', 'publication_title', 'publication_year',
            'company_funding', 'uses_3d_models'
        ]
        
        # Filter existing columns
        available_cols = [col for col in export_columns if col in df.columns]
        export_df = df[available_cols].copy()
        
        # Rename for clarity
        column_rename = {
            'rank': 'Rank',
            'propensity_score': 'Score',
            'name': 'Name',
            'title': 'Job Title',
            'company': 'Company',
            'location': 'Location',
            'company_hq': 'Company HQ',
            'email': 'Email',
            'linkedin': 'LinkedIn URL',
            'recent_publication': 'Recent Publication',
            'publication_title': 'Publication Title',
            'publication_year': 'Year',
            'company_funding': 'Funding Stage',
            'uses_3d_models': 'Uses 3D Models'
        }
        
        export_df = export_df.rename(columns=column_rename)
        
        # Convert booleans to Yes/No
        for col in export_df.columns:
            if export_df[col].dtype == 'bool':
                export_df[col] = export_df[col].map({True: 'Yes', False: 'No'})
        
        # Fill NaN
        export_df = export_df.fillna('N/A')
        
        # Sort by rank
        if 'Rank' in export_df.columns:
            export_df = export_df.sort_values('Rank')
        
        return export_df
    
    def to_csv_for_sheets(self, df: pd.DataFrame) -> str:
        """
        Export to CSV format optimized for Google Sheets
        
        Args:
            df: DataFrame to export
            
        Returns:
            CSV string
        """
        formatted_df = self.prepare_for_sheets(df)
        return formatted_df.to_csv(index=False)
    
    def get_sheets_instructions(self) -> str:
        """
        Get instructions for uploading to Google Sheets
        
        Returns:
            Instructions text
        """
        return """
GOOGLE SHEETS UPLOAD INSTRUCTIONS:
==================================

1. Download the CSV file from the app
2. Go to Google Sheets (sheets.google.com)
3. Create new spreadsheet
4. File → Import → Upload
5. Select the CSV file
6. Import location: "Replace current sheet"
7. Click "Import data"
8. Format the sheet:
   - Make header row bold
   - Apply color coding to Score column:
     * Green (70-100): High Priority
     * Yellow (50-69): Medium Priority
     * Red (0-49): Low Priority
9. Share → Get link → Anyone with link can view
10. Copy the link and include in your email to Euprime

Alternative: Use the exported Excel file which has formatting pre-applied!
"""