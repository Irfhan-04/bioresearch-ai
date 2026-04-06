"""
Export utilities for lead data
Supports CSV, Excel, and formatted exports
"""

import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime
from typing import Optional, List


class ExportHelper:
    """
    Handles data export in various formats
    """
    
    def __init__(self):
        self.export_columns = [
            'rank', 'propensity_score', 'name', 'title', 'company',
            'location', 'company_hq', 'email', 'linkedin',
            'recent_publication', 'publication_title', 'company_funding'
        ]
    
    def to_csv(
        self,
        df: pd.DataFrame,
        include_columns: Optional[List[str]] = None
    ) -> str:
        """
        Export DataFrame to CSV string
        
        Args:
            df: DataFrame to export
            include_columns: Specific columns to include (None = all)
            
        Returns:
            CSV string
        """
        if include_columns:
            export_df = df[include_columns].copy()
        else:
            # Use default export columns that exist in df
            available_cols = [col for col in self.export_columns if col in df.columns]
            export_df = df[available_cols].copy()
        
        # Format for export
        export_df = self._format_for_export(export_df)
        
        return export_df.to_csv(index=False)
    
    def to_excel(
        self,
        df: pd.DataFrame,
        include_columns: Optional[List[str]] = None,
        sheet_name: str = "Leads"
    ) -> bytes:
        """
        Export DataFrame to Excel bytes
        
        Args:
            df: DataFrame to export
            include_columns: Specific columns to include (None = all)
            sheet_name: Name of Excel sheet
            
        Returns:
            Excel file as bytes
        """
        if include_columns:
            export_df = df[include_columns].copy()
        else:
            available_cols = [col for col in self.export_columns if col in df.columns]
            export_df = df[available_cols].copy()
        
        # Format for export
        export_df = self._format_for_export(export_df)
        
        # Create Excel file in memory
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            
            # Add formatting
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#1E88E5',
                'font_color': 'white',
                'border': 1
            })
            
            # Format header
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Set column widths
            column_widths = {
                'rank': 8,
                'propensity_score': 12,
                'name': 20,
                'title': 30,
                'company': 25,
                'location': 20,
                'email': 30,
                'linkedin': 35,
                'publication_title': 40
            }
            
            for col_num, col_name in enumerate(export_df.columns):
                width = column_widths.get(col_name, 15)
                worksheet.set_column(col_num, col_num, width)
            
            # Add score color formatting
            if 'propensity_score' in export_df.columns:
                score_col = export_df.columns.get_loc('propensity_score')
                
                # High score format (green)
                high_format = workbook.add_format({
                    'bg_color': '#C6EFCE',
                    'font_color': '#006100'
                })
                
                # Medium score format (yellow)
                medium_format = workbook.add_format({
                    'bg_color': '#FFEB9C',
                    'font_color': '#9C6500'
                })
                
                # Low score format (red)
                low_format = workbook.add_format({
                    'bg_color': '#FFC7CE',
                    'font_color': '#9C0006'
                })
                
                # Apply conditional formatting
                worksheet.conditional_format(
                    1, score_col, len(export_df), score_col,
                    {
                        'type': 'cell',
                        'criteria': '>=',
                        'value': 70,
                        'format': high_format
                    }
                )
                worksheet.conditional_format(
                    1, score_col, len(export_df), score_col,
                    {
                        'type': 'cell',
                        'criteria': 'between',
                        'minimum': 50,
                        'maximum': 69,
                        'format': medium_format
                    }
                )
                worksheet.conditional_format(
                    1, score_col, len(export_df), score_col,
                    {
                        'type': 'cell',
                        'criteria': '<',
                        'value': 50,
                        'format': low_format
                    }
                )
        
        return output.getvalue()
    
    def _format_for_export(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format DataFrame for clean export
        
        Args:
            df: DataFrame to format
            
        Returns:
            Formatted DataFrame
        """
        export_df = df.copy()
        
        # Rename columns to be more human-readable
        column_rename = {
            'rank': 'Rank',
            'propensity_score': 'Score',
            'name': 'Name',
            'title': 'Title',
            'company': 'Company',
            'location': 'Location',
            'company_hq': 'Company HQ',
            'email': 'Email',
            'linkedin': 'LinkedIn',
            'recent_publication': 'Recent Publication',
            'publication_title': 'Publication',
            'publication_year': 'Year',
            'company_funding': 'Funding Stage'
        }
        
        export_df = export_df.rename(columns=column_rename)
        
        # Convert boolean to Yes/No
        for col in export_df.columns:
            if export_df[col].dtype == 'bool':
                export_df[col] = export_df[col].map({True: 'Yes', False: 'No'})
        
        # Clean up N/A values
        export_df = export_df.fillna('N/A')
        
        return export_df
    
    def create_summary_report(self, df: pd.DataFrame) -> str:
        """
        Create a text summary report
        
        Args:
            df: DataFrame with lead data
            
        Returns:
            Text report
        """
        total_leads = len(df)
        avg_score = df['propensity_score'].mean()
        
        high_priority = len(df[df['propensity_score'] >= 70])
        medium_priority = len(df[(df['propensity_score'] >= 50) & (df['propensity_score'] < 70)])
        low_priority = len(df[df['propensity_score'] < 50])
        
        recent_pubs = df['recent_publication'].sum() if 'recent_publication' in df else 0
        
        # Top locations
        top_locations = df['location'].value_counts().head(5)
        
        # Top companies
        top_companies = df['company'].value_counts().head(5)
        
        report = f"""
LEAD GENERATION SUMMARY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

OVERVIEW
--------
Total Leads: {total_leads}
Average Score: {avg_score:.1f}/100

PRIORITY DISTRIBUTION
--------------------
🟢 High Priority (70+):    {high_priority} leads ({high_priority/total_leads*100:.1f}%)
🟡 Medium Priority (50-69): {medium_priority} leads ({medium_priority/total_leads*100:.1f}%)
🔴 Low Priority (<50):      {low_priority} leads ({low_priority/total_leads*100:.1f}%)

KEY METRICS
-----------
Leads with Recent Publications: {recent_pubs} ({recent_pubs/total_leads*100:.1f}%)
Well-Funded Companies: {len(df[df['company_funding'].isin(['Series A', 'Series B', 'Series C'])])}

TOP 5 LOCATIONS
---------------
{self._format_value_counts(top_locations)}

TOP 5 COMPANIES
---------------
{self._format_value_counts(top_companies)}

TOP 10 LEADS
------------
"""
        
        # Add top 10 leads
        top_leads = df.nsmallest(10, 'rank')[['rank', 'propensity_score', 'name', 'title', 'company']]
        
        for _, lead in top_leads.iterrows():
            report += f"{lead['rank']}. {lead['name']} ({lead['propensity_score']}/100)\n"
            report += f"   {lead['title']} at {lead['company']}\n\n"
        
        report += "================================================================================\n"
        
        return report
    
    def _format_value_counts(self, value_counts: pd.Series) -> str:
        """Helper to format value counts for report"""
        result = ""
        for value, count in value_counts.items():
            result += f"{value}: {count}\n"
        return result.strip()
    
    def to_json(self, df: pd.DataFrame) -> str:
        """
        Export DataFrame to JSON string
        
        Args:
            df: DataFrame to export
            
        Returns:
            JSON string
        """
        available_cols = [col for col in self.export_columns if col in df.columns]
        export_df = df[available_cols].copy()
        
        return export_df.to_json(orient='records', indent=2)


# Example usage
if __name__ == "__main__":
    # Test with sample data
    sample_df = pd.DataFrame({
        'rank': [1, 2, 3],
        'propensity_score': [95, 85, 75],
        'name': ['Dr. Sarah Mitchell', 'Dr. James Chen', 'Dr. Emily Rodriguez'],
        'title': ['Director of Toxicology', 'Head of Preclinical Safety', 'Principal Scientist'],
        'company': ['Moderna', 'Vertex', 'BioMarin'],
        'location': ['Cambridge, MA', 'Boston, MA', 'San Rafael, CA'],
        'email': ['sarah@moderna.com', 'james@vrtx.com', 'emily@biomarin.com'],
        'recent_publication': [True, True, False],
        'company_funding': ['Public', 'Public', 'Series B']
    })
    
    exporter = ExportHelper()
    
    # Test CSV export
    csv_data = exporter.to_csv(sample_df)
    print("CSV Export:")
    print(csv_data[:200])
    
    # Test summary report
    report = exporter.create_summary_report(sample_df)
    print("\nSummary Report:")
    print(report)