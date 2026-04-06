"""
Data Validation
"""
def validate_lead_data(lead: dict) -> tuple[bool, list]:
    """
    Validate lead data completeness and format
    
    Args:
        lead: Dictionary with lead information
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Required fields
    required_fields = ['name', 'title', 'company', 'location']
    for field in required_fields:
        if field not in lead or not lead[field]:
            errors.append(f"Missing required field: {field}")
    
    # Email format validation
    if 'email' in lead and lead['email'] and lead['email'] != 'N/A':
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, lead['email']):
            errors.append(f"Invalid email format: {lead['email']}")
    
    # LinkedIn URL validation
    if 'linkedin' in lead and lead['linkedin'] and lead['linkedin'] != 'N/A':
        if not lead['linkedin'].startswith(('linkedin.com', 'www.linkedin.com', 'https://linkedin.com')):
            errors.append(f"Invalid LinkedIn URL: {lead['linkedin']}")
    
    # Year validation
    if 'publication_year' in lead and lead['publication_year']:
        current_year = datetime.now().year
        if lead['publication_year'] > current_year or lead['publication_year'] < 1950:
            errors.append(f"Invalid publication year: {lead['publication_year']}")
    
    return len(errors) == 0, errors


def validate_dataframe(df: pd.DataFrame) -> dict:
    """
    Validate entire DataFrame
    
    Returns:
        Dictionary with validation results
    """
    results = {
        'total_rows': len(df),
        'valid_rows': 0,
        'invalid_rows': 0,
        'errors': []
    }
    
    for idx, row in df.iterrows():
        is_valid, errors = validate_lead_data(row.to_dict())
        
        if is_valid:
            results['valid_rows'] += 1
        else:
            results['invalid_rows'] += 1
            results['errors'].append({
                'row': idx,
                'name': row.get('name', 'Unknown'),
                'errors': errors
            })
    
    return results