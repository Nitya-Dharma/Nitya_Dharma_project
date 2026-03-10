"""
CSV Upload Services for Master Data

Handles CSV-based bulk upload for:
- Cities
- Mandals
- Local Areas
- Pooja Categories
- Poojas

All uploads are Super Admin only and atomic per file.
"""

import csv
import io
import logging
from typing import Dict, List, Tuple, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import City, Mandal, LocalArea, PoojaCategory, Pooja

logger = logging.getLogger(__name__)


class CSVUploadResult:
    """Result of a CSV upload operation."""
    
    def __init__(self):
        self.total_rows = 0
        self.inserted = 0
        self.skipped = 0
        self.failed = 0
        self.failure_reasons: List[Dict[str, str]] = []
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary for JSON response."""
        return {
            'total_rows': self.total_rows,
            'inserted': self.inserted,
            'skipped': self.skipped,
            'failed': self.failed,
            'failure_reasons': self.failure_reasons,
        }


def parse_csv_file(file) -> List[Dict[str, str]]:
    """
    Parse CSV file and return list of dictionaries.
    
    Handles multiple encodings: UTF-8, UTF-8-BOM, Windows-1252, CP1252, ISO-8859-1
    
    Args:
        file: Django uploaded file object
        
    Returns:
        List of dictionaries, one per row
    """
    try:
        # Read file content as bytes first
        file.seek(0)  # Reset file pointer
        content_bytes = file.read()
        
        # Try different encodings in order of likelihood
        encodings_to_try = [
            'utf-8-sig',  # UTF-8 with BOM (most common for Excel exports)
            'utf-8',      # Standard UTF-8
            'windows-1252',  # Windows encoding (common for Excel on Windows)
            'cp1252',     # Windows code page 1252
            'iso-8859-1', # Latin-1
            'latin1',     # Alternative name
        ]
        
        content = None
        encoding_used = None
        
        for encoding in encodings_to_try:
            try:
                content = content_bytes.decode(encoding)
                encoding_used = encoding
                logger.info(f"Successfully decoded CSV file using encoding: {encoding}")
                break
            except (UnicodeDecodeError, LookupError):
                continue
        
        if content is None:
            raise ValidationError(
                "Could not decode CSV file. Please save your file as UTF-8 or UTF-8-BOM encoding. "
                "In Excel: File > Save As > CSV UTF-8 (Comma delimited) (*.csv)"
            )
        
        # Normalize line endings first (Windows \r\n -> \n, old Mac \r -> \n)
        # Don't replace newlines - let CSV parser handle them correctly
        # CSV parser knows: newlines in quotes = field content, newlines outside = row separators
        content_normalized = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Parse CSV with robust settings
        # Create StringIO object for CSV reader
        csv_file = io.StringIO(content_normalized)
        
        try:
            # Try standard CSV parsing first
            reader = csv.DictReader(
                csv_file,
                delimiter=',',
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
                skipinitialspace=True,
                strict=False  # Be lenient with malformed CSV
            )
            
            rows = []
            for row in reader:
                # Trim whitespace from all values and handle None
                cleaned_row = {}
                for k, v in row.items():
                    if k is None:
                        continue  # Skip None keys
                    key = k.strip() if k else ''
                    value = v.strip() if v else ''
                    # Remove any BOM or zero-width characters
                    key = key.replace('\ufeff', '').replace('\u200b', '')
                    value = value.replace('\ufeff', '').replace('\u200b', '')
                    # Replace any remaining problematic newlines in values with space
                    value = value.replace('\n', ' ').replace('\r', ' ')
                    cleaned_row[key] = value
                
                # Only add row if it has at least one non-empty value (skip completely empty rows)
                if any(v for v in cleaned_row.values() if v):
                    rows.append(cleaned_row)
                else:
                    logger.debug(f"Skipping empty row: {cleaned_row}")
        except csv.Error as csv_err:
            # If CSV parsing fails due to newlines, try a more lenient approach
            logger.warning(f"Standard CSV parsing failed: {csv_err}. Trying lenient parsing...")
            
            # Use a more lenient approach: split by commas but respect quotes
            rows = []
            lines = content_normalized.split('\n')
            if len(lines) < 2:
                raise ValidationError("CSV file must have at least a header row and one data row")
            
            # Get header from first line
            header_line = lines[0]
            # Try to parse header with csv.reader
            header_reader = csv.reader([header_line], delimiter=',', quotechar='"')
            try:
                headers = next(header_reader)
                headers = [h.strip().replace('\ufeff', '').replace('\u200b', '') for h in headers]
            except:
                # Fallback: simple split
                headers = [h.strip() for h in header_line.split(',')]
            
            # Parse data rows
            for line_num, line in enumerate(lines[1:], start=2):
                if not line.strip():
                    continue  # Skip empty lines
                
                try:
                    row_reader = csv.reader([line], delimiter=',', quotechar='"', skipinitialspace=True)
                    values = next(row_reader)
                    # Pad or truncate to match header length
                    while len(values) < len(headers):
                        values.append('')
                    values = values[:len(headers)]
                    
                    cleaned_row = {}
                    for i, header in enumerate(headers):
                        value = values[i].strip() if i < len(values) else ''
                        value = value.replace('\ufeff', '').replace('\u200b', '')
                        value = value.replace('\n', ' ').replace('\r', ' ')
                        cleaned_row[header] = value
                    
                    # Only add row if it has at least one non-empty value (skip completely empty rows)
                    if any(v for v in cleaned_row.values() if v):
                        rows.append(cleaned_row)
                    else:
                        logger.debug(f"Skipping empty row at line {line_num}")
                except Exception as e:
                    logger.warning(f"Error parsing line {line_num}: {e}")
                    # Skip problematic lines but continue
                    continue
        
        if not rows:
            # Log more details for debugging
            logger.error(
                f"CSV file appears empty after parsing. "
                f"Encoding used: {encoding_used}, "
                f"Content length: {len(content)} chars, "
                f"Lines after split: {len(content_normalized.split(chr(10)))}"
            )
            raise ValidationError(
                "CSV file is empty or has no data rows (only header). "
                "Please ensure your CSV file has at least one data row after the header row. "
                "Empty rows are automatically skipped. "
                f"File encoding detected: {encoding_used}. "
                "If your file has data, please check that rows are not completely empty."
            )
        
        logger.info(f"Parsed {len(rows)} rows from CSV file (encoding: {encoding_used})")
        return rows
        
    except ValidationError:
        raise  # Re-raise validation errors as-is
    except Exception as e:
        logger.error(f"Error parsing CSV file: {e}", exc_info=True)
        raise ValidationError(f"Invalid CSV file format: {str(e)}. Please ensure the file is a valid CSV with proper encoding.")


@transaction.atomic
def upload_cities_csv(file, actor=None) -> CSVUploadResult:
    """
    Upload cities from CSV file.
    
    Expected CSV format:
    name,state,tier,status
    
    Args:
        file: Django uploaded file object
        actor: User performing the upload (for audit)
        
    Returns:
        CSVUploadResult with upload statistics
    """
    result = CSVUploadResult()
    rows = parse_csv_file(file)
    result.total_rows = len(rows)
    
    # Validate CSV has required columns
    if rows:
        required_columns = ['name']
        first_row_keys = set(rows[0].keys())
        missing_columns = [col for col in required_columns if col not in first_row_keys]
        if missing_columns:
            raise ValidationError(
                f"CSV file is missing required columns: {', '.join(missing_columns)}. "
                f"Found columns: {', '.join(first_row_keys)}. "
                f"Note: Extra columns (like 'tier') will be ignored."
            )
        
        # Log extra columns that will be ignored
        expected_columns = {'name', 'state', 'status'}
        extra_columns = first_row_keys - expected_columns
        if extra_columns:
            logger.info(f"CSV contains extra columns that will be ignored: {', '.join(extra_columns)}")
    
    for row_num, row in enumerate(rows, start=2):  # Start at 2 (row 1 is header)
        try:
            name = row.get('name', '').strip()
            if not name:
                result.skipped += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': 'Missing name field'
                })
                continue
            
            # Check for duplicates (case-insensitive)
            existing_city = City.objects.filter(name__iexact=name).first()
            if existing_city:
                result.skipped += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': f'City "{name}" already exists (ID: {existing_city.id})'
                })
                continue
            
            # Parse status (default to ACTIVE)
            status_str = row.get('status', 'active').strip().lower()
            if status_str in ['active', '1', 'true', 'yes', '']:
                status = City.STATUS_ACTIVE
                is_active = True
            elif status_str in ['inactive', '0', 'false', 'no']:
                status = City.STATUS_INACTIVE
                is_active = False
            else:
                status = City.STATUS_ACTIVE
                is_active = True
            
            # Create city
            city = City(
                name=name,
                state=row.get('state', '').strip() or None,
                status=status,
                is_active=is_active
            )
            
            city.save()
            result.inserted += 1
            
        except Exception as e:
            result.failed += 1
            result.failure_reasons.append({
                'row': row_num,
                'reason': str(e)
            })
            logger.error(f"Error processing city row {row_num}: {e}")
    
    logger.info(f"City CSV upload completed: {result.to_dict()}")
    return result


@transaction.atomic
def upload_mandals_csv(file, actor=None) -> CSVUploadResult:
    """
    Upload mandals from CSV file.
    
    Expected CSV format:
    city,name,status
    
    Args:
        file: Django uploaded file object
        actor: User performing the upload (for audit)
        
    Returns:
        CSVUploadResult with upload statistics
    """
    result = CSVUploadResult()
    rows = parse_csv_file(file)
    result.total_rows = len(rows)
    
    # Validate CSV has required columns
    if rows:
        required_columns = ['city', 'name']
        first_row_keys = set(rows[0].keys())
        missing_columns = [col for col in required_columns if col not in first_row_keys]
        if missing_columns:
            raise ValidationError(
                f"CSV file is missing required columns: {', '.join(missing_columns)}. "
                f"Found columns: {', '.join(first_row_keys)}"
            )
    
    for row_num, row in enumerate(rows, start=2):
        try:
            city_name = row.get('city', '').strip()
            mandal_name = row.get('name', '').strip()
            
            if not city_name or not mandal_name:
                result.skipped += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': 'Missing city or name field'
                })
                continue
            
            # Find city (case-insensitive)
            city = City.objects.filter(name__iexact=city_name).first()
            if not city:
                result.failed += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': f'City "{city_name}" not found. Please upload cities first.'
                })
                continue
            
            # Check for duplicates (case-insensitive)
            existing_mandal = Mandal.objects.filter(name__iexact=mandal_name, city=city).first()
            if existing_mandal:
                result.skipped += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': f'Mandal "{mandal_name}" already exists in {city_name} (ID: {existing_mandal.id})'
                })
                continue
            
            # Create mandal
            mandal = Mandal(
                name=mandal_name,
                city=city,
                status=row.get('status', 'active').strip().lower() or 'active',
                is_active=row.get('status', 'active').strip().lower() != 'inactive'
            )
            
            if mandal.status not in [Mandal.STATUS_ACTIVE, Mandal.STATUS_INACTIVE]:
                mandal.status = Mandal.STATUS_ACTIVE
            
            mandal.save()
            result.inserted += 1
            
        except Exception as e:
            result.failed += 1
            result.failure_reasons.append({
                'row': row_num,
                'reason': str(e)
            })
            logger.error(f"Error processing mandal row {row_num}: {e}")
    
    logger.info(f"Mandal CSV upload completed: {result.to_dict()}")
    return result


@transaction.atomic
def upload_local_areas_csv(file, actor=None) -> CSVUploadResult:
    """
    Upload local areas from CSV file.
    
    Expected CSV format:
    city,mandal,name,status
    
    Note: mandal is optional
    
    Args:
        file: Django uploaded file object
        actor: User performing the upload (for audit)
        
    Returns:
        CSVUploadResult with upload statistics
    """
    result = CSVUploadResult()
    rows = parse_csv_file(file)
    result.total_rows = len(rows)
    
    for row_num, row in enumerate(rows, start=2):
        try:
            city_name = row.get('city', '').strip()
            mandal_name = row.get('mandal', '').strip()
            area_name = row.get('name', '').strip()
            
            if not city_name or not area_name:
                result.skipped += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': 'Missing city or name field'
                })
                continue
            
            # Find city
            city = City.objects.filter(name__iexact=city_name).first()
            if not city:
                result.failed += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': f'City "{city_name}" not found'
                })
                continue
            
            # Find mandal if provided
            mandal = None
            if mandal_name:
                mandal = Mandal.objects.filter(name__iexact=mandal_name, city=city).first()
                if not mandal:
                    result.failed += 1
                    result.failure_reasons.append({
                        'row': row_num,
                        'reason': f'Mandal "{mandal_name}" not found in {city_name}'
                    })
                    continue
            
            # Check for duplicates
            if LocalArea.objects.filter(name__iexact=area_name, city=city).exists():
                result.skipped += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': f'Local area "{area_name}" already exists in {city_name}'
                })
                continue
            
            # Create local area
            area = LocalArea(
                name=area_name,
                city=city,
                mandal=mandal,
                status=row.get('status', 'active').strip().lower() or 'active',
                is_active=row.get('status', 'active').strip().lower() != 'inactive'
            )
            
            if area.status not in [LocalArea.STATUS_ACTIVE, LocalArea.STATUS_INACTIVE]:
                area.status = LocalArea.STATUS_ACTIVE
            
            area.save()
            result.inserted += 1
            
        except Exception as e:
            result.failed += 1
            result.failure_reasons.append({
                'row': row_num,
                'reason': str(e)
            })
            logger.error(f"Error processing local area row {row_num}: {e}")
    
    logger.info(f"Local area CSV upload completed: {result.to_dict()}")
    return result


@transaction.atomic
def upload_pooja_categories_csv(file, actor=None) -> CSVUploadResult:
    """
    Upload pooja categories from CSV file.
    
    Expected CSV format:
    name,status
    
    Args:
        file: Django uploaded file object
        actor: User performing the upload (for audit)
        
    Returns:
        CSVUploadResult with upload statistics
    """
    result = CSVUploadResult()
    rows = parse_csv_file(file)
    result.total_rows = len(rows)
    
    for row_num, row in enumerate(rows, start=2):
        try:
            name = row.get('name', '').strip()
            if not name:
                result.skipped += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': 'Missing name field'
                })
                continue
            
            # Check for duplicates
            if PoojaCategory.objects.filter(name__iexact=name).exists():
                result.skipped += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': f'Pooja category "{name}" already exists'
                })
                continue
            
            status_val = (row.get('status', 'active').strip().lower() or 'active')
            if status_val not in [PoojaCategory.STATUS_ACTIVE, PoojaCategory.STATUS_INACTIVE]:
                status_val = PoojaCategory.STATUS_ACTIVE
            category = PoojaCategory(
                name=name,
                status=status_val,
                is_active=(status_val == PoojaCategory.STATUS_ACTIVE),
            )
            category.save()
            result.inserted += 1
            
        except Exception as e:
            result.failed += 1
            result.failure_reasons.append({
                'row': row_num,
                'reason': str(e)
            })
            logger.error(f"Error processing pooja category row {row_num}: {e}")
    
    logger.info(f"Pooja category CSV upload completed: {result.to_dict()}")
    return result


@transaction.atomic
def upload_poojas_csv(file, actor=None) -> CSVUploadResult:
    """
    Upload poojas from CSV file.
    
    Expected CSV format:
    name,category,status
    
    Note: category can be either category name (FK lookup) or category code (deprecated)
    
    Args:
        file: Django uploaded file object
        actor: User performing the upload (for audit)
        
    Returns:
        CSVUploadResult with upload statistics
    """
    result = CSVUploadResult()
    rows = parse_csv_file(file)
    result.total_rows = len(rows)
    
    for row_num, row in enumerate(rows, start=2):
        try:
            name = row.get('name', '').strip()
            if not name:
                result.skipped += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': 'Missing name field'
                })
                continue
            
            # Check for duplicates
            if Pooja.objects.filter(name__iexact=name).exists():
                result.skipped += 1
                result.failure_reasons.append({
                    'row': row_num,
                    'reason': f'Pooja "{name}" already exists'
                })
                continue
            
            # Find category if provided
            pooja_category = None
            category_code = None
            category_name = row.get('category', '').strip()
            
            if category_name:
                # Try to find by PoojaCategory name first
                pooja_category = PoojaCategory.objects.filter(name__iexact=category_name).first()
                
                # If not found, try to match with deprecated category codes
                if not pooja_category:
                    category_mapping = {
                        'daily_household': 'A. Daily & Common Household Poojas',
                        'house_property_vehicle': 'B. House, Property & Vehicle Poojas',
                        'life_samskaras': 'C. Important Life Samskaras',
                        'festival_temple': 'D. Festival & Temple Poojas',
                        'homams': 'E. Homams / Fire Rituals',
                        'yagnas': 'F. Yagnas',
                    }
                    if category_name in category_mapping:
                        pooja_category = PoojaCategory.objects.filter(
                            name__iexact=category_mapping[category_name]
                        ).first()
                        if pooja_category:
                            category_code = category_name
                    else:
                        # Try direct match with category display names
                        for code, display_name in category_mapping.items():
                            if category_name.lower() in display_name.lower():
                                pooja_category = PoojaCategory.objects.filter(
                                    name__iexact=display_name
                                ).first()
                                if pooja_category:
                                    category_code = code
                                    break
            
            # Create pooja
            pooja = Pooja(
                name=name,
                pooja_category=pooja_category,
                category=category_code,  # Set deprecated field for backward compatibility
                status=row.get('status', 'active').strip().lower() or 'active',
                is_active=row.get('status', 'active').strip().lower() != 'inactive'
            )
            
            if pooja.status not in [Pooja.STATUS_ACTIVE, Pooja.STATUS_INACTIVE]:
                pooja.status = Pooja.STATUS_ACTIVE
            
            pooja.save()
            result.inserted += 1
            
        except Exception as e:
            result.failed += 1
            result.failure_reasons.append({
                'row': row_num,
                'reason': str(e)
            })
            logger.error(f"Error processing pooja row {row_num}: {e}")
    
    logger.info(f"Pooja CSV upload completed: {result.to_dict()}")
    return result

