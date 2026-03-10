"""
Master Data Views

Super Admin only views for CSV upload and master data management.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from accounts.decorators import admin_required
from .models import City, Mandal, LocalArea, PoojaCategory, Pooja
from .services_csv_upload import (
    upload_cities_csv,
    upload_mandals_csv,
    upload_local_areas_csv,
    upload_pooja_categories_csv,
    upload_poojas_csv,
)

logger = logging.getLogger(__name__)


@login_required
@admin_required
def master_data_management(request):
    """
    Master Data Management dashboard (Super Admin only).
    
    REDIRECTS to Super Admin Dashboard Master Data page.
    This maintains backward compatibility with old URLs.
    """
    if not request.user.is_superuser:
        messages.error(request, 'Only Super Admins can access this page.')
        return redirect('core:home')
    
    # Redirect to Super Admin Dashboard Master Data page
    return redirect('module5_dashboards:master_data_management')


@login_required
@admin_required
@require_http_methods(["GET", "POST"])
def upload_cities(request):
    """Upload cities from CSV (Super Admin only)."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Only Super Admins can upload cities'}, status=403)
    
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'No CSV file provided.')
            return redirect('masterdata:management')
        
        try:
            # PART 4 FIX: Centralized file upload validation
            from core.file_upload_security import validate_csv_upload
            from django.core.exceptions import ValidationError
            try:
                sanitized_filename, validated_file = validate_csv_upload(request.FILES['csv_file'])
            except ValidationError as e:
                messages.error(request, f'CSV file validation failed: {str(e)}')
                return redirect('masterdata:management')
            
            result = upload_cities_csv(validated_file, actor=request.user)
            messages.success(
                request,
                f'Upload complete: {result.inserted} inserted, {result.skipped} skipped, {result.failed} failed.'
            )
            
            if result.failure_reasons:
                # Show first 5 failure reasons
                failure_msg = '; '.join([f"Row {fr['row']}: {fr['reason']}" for fr in result.failure_reasons[:5]])
                if len(result.failure_reasons) > 5:
                    failure_msg += f' ... and {len(result.failure_reasons) - 5} more'
                messages.warning(request, f'Some rows failed: {failure_msg}')
            
        except ValidationError as e:
            messages.error(request, f'Validation error: {str(e)}')
        except Exception as e:
            logger.exception("Error uploading cities")
            error_msg = str(e)
            # Make error messages more user-friendly
            if 'codec' in error_msg.lower() or 'decode' in error_msg.lower():
                error_msg = (
                    "File encoding error. Please save your CSV file as UTF-8. "
                    "In Excel: File > Save As > CSV UTF-8 (Comma delimited) (*.csv)"
                )
            messages.error(request, f'Error uploading cities: {error_msg}')
        
        return redirect('masterdata:management')
    
    # GET: No standalone template; redirect to management dashboard (which has the upload form)
    return redirect('masterdata:management')


@login_required
@admin_required
@require_http_methods(["GET", "POST"])
def upload_mandals(request):
    """Upload mandals from CSV (Super Admin only)."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Only Super Admins can upload mandals'}, status=403)
    
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'No CSV file provided.')
            return redirect('masterdata:management')
        
        try:
            # PART 4 FIX: Centralized file upload validation
            from core.file_upload_security import validate_csv_upload
            from django.core.exceptions import ValidationError
            try:
                sanitized_filename, validated_file = validate_csv_upload(request.FILES['csv_file'])
            except ValidationError as e:
                messages.error(request, f'CSV file validation failed: {str(e)}')
                return redirect('masterdata:management')
            
            result = upload_mandals_csv(validated_file, actor=request.user)
            messages.success(
                request,
                f'Upload complete: {result.inserted} inserted, {result.skipped} skipped, {result.failed} failed.'
            )
            
            if result.failure_reasons:
                failure_msg = '; '.join([f"Row {fr['row']}: {fr['reason']}" for fr in result.failure_reasons[:5]])
                if len(result.failure_reasons) > 5:
                    failure_msg += f' ... and {len(result.failure_reasons) - 5} more'
                messages.warning(request, f'Some rows failed: {failure_msg}')
            
        except Exception as e:
            messages.error(request, f'Error uploading mandals: {str(e)}')
        
        return redirect('masterdata:management')
    
    # GET: Redirect to management dashboard (which has the upload form)
    return redirect('masterdata:management')


@login_required
@admin_required
@require_http_methods(["GET", "POST"])
def upload_local_areas(request):
    """Upload local areas from CSV (Super Admin only)."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Only Super Admins can upload local areas'}, status=403)
    
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'No CSV file provided.')
            return redirect('masterdata:management')
        
        try:
            # PART 4 FIX: Centralized file upload validation
            from core.file_upload_security import validate_csv_upload
            from django.core.exceptions import ValidationError
            try:
                sanitized_filename, validated_file = validate_csv_upload(request.FILES['csv_file'])
            except ValidationError as e:
                messages.error(request, f'CSV file validation failed: {str(e)}')
                return redirect('masterdata:management')
            
            result = upload_local_areas_csv(validated_file, actor=request.user)
            messages.success(
                request,
                f'Upload complete: {result.inserted} inserted, {result.skipped} skipped, {result.failed} failed.'
            )
            
            if result.failure_reasons:
                failure_msg = '; '.join([f"Row {fr['row']}: {fr['reason']}" for fr in result.failure_reasons[:5]])
                if len(result.failure_reasons) > 5:
                    failure_msg += f' ... and {len(result.failure_reasons) - 5} more'
                messages.warning(request, f'Some rows failed: {failure_msg}')
            
        except Exception as e:
            messages.error(request, f'Error uploading local areas: {str(e)}')
        
        return redirect('masterdata:management')
    
    # GET: Redirect to management dashboard (which has the upload form)
    return redirect('masterdata:management')


@login_required
@admin_required
@require_http_methods(["GET", "POST"])
def upload_pooja_categories(request):
    """Upload pooja categories from CSV (Super Admin only)."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Only Super Admins can upload pooja categories'}, status=403)
    
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'No CSV file provided.')
            return redirect('masterdata:management')
        
        try:
            # PART 4 FIX: Centralized file upload validation
            from core.file_upload_security import validate_csv_upload
            from django.core.exceptions import ValidationError
            try:
                sanitized_filename, validated_file = validate_csv_upload(request.FILES['csv_file'])
            except ValidationError as e:
                messages.error(request, f'CSV file validation failed: {str(e)}')
                return redirect('masterdata:management')
            
            result = upload_pooja_categories_csv(validated_file, actor=request.user)
            messages.success(
                request,
                f'Upload complete: {result.inserted} inserted, {result.skipped} skipped, {result.failed} failed.'
            )
            
            if result.failure_reasons:
                failure_msg = '; '.join([f"Row {fr['row']}: {fr['reason']}" for fr in result.failure_reasons[:5]])
                if len(result.failure_reasons) > 5:
                    failure_msg += f' ... and {len(result.failure_reasons) - 5} more'
                messages.warning(request, f'Some rows failed: {failure_msg}')
            
        except Exception as e:
            messages.error(request, f'Error uploading pooja categories: {str(e)}')
        
        return redirect('masterdata:management')
    
    # GET: Redirect to management dashboard (which has the upload form)
    return redirect('masterdata:management')


@login_required
@admin_required
@require_http_methods(["GET", "POST"])
def upload_poojas(request):
    """Upload poojas from CSV (Super Admin only)."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Only Super Admins can upload poojas'}, status=403)
    
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'No CSV file provided.')
            return redirect('masterdata:management')
        
        try:
            # PART 4 FIX: Centralized file upload validation
            from core.file_upload_security import validate_csv_upload
            from django.core.exceptions import ValidationError
            try:
                sanitized_filename, validated_file = validate_csv_upload(request.FILES['csv_file'])
            except ValidationError as e:
                messages.error(request, f'CSV file validation failed: {str(e)}')
                return redirect('masterdata:management')
            
            result = upload_poojas_csv(validated_file, actor=request.user)
            messages.success(
                request,
                f'Upload complete: {result.inserted} inserted, {result.skipped} skipped, {result.failed} failed.'
            )
            
            if result.failure_reasons:
                failure_msg = '; '.join([f"Row {fr['row']}: {fr['reason']}" for fr in result.failure_reasons[:5]])
                if len(result.failure_reasons) > 5:
                    failure_msg += f' ... and {len(result.failure_reasons) - 5} more'
                messages.warning(request, f'Some rows failed: {failure_msg}')
            
        except Exception as e:
            messages.error(request, f'Error uploading poojas: {str(e)}')
        
        return redirect('masterdata:management')
    
    # GET: Redirect to management dashboard (which has the upload form)
    return redirect('masterdata:management')


@login_required
@admin_required
def download_sample_csv(request, entity_type):
    """
    Download sample CSV file for a given entity type.
    
    Args:
        entity_type: One of 'cities', 'mandals', 'local_areas', 'pooja_categories', 'poojas'
    """
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Only Super Admins can download sample CSVs'}, status=403)
    
    samples = {
        'cities': 'name,state,status\nMumbai,Maharashtra,active\nDelhi,Delhi,active\nBangalore,Karnataka,active',
        'mandals': 'city,name,status\nMumbai,Andheri,active\nMumbai,Bandra,active\nDelhi,Central Delhi,active',
        'local_areas': 'mandal,name,status\nAndheri,Andheri East,active\nAndheri,Andheri West,active\nBandra,Bandra East,active',
        'pooja_categories': 'name,status\nDaily & Common Household Poojas,active\nHouse, Property & Vehicle Poojas,active',
        'poojas': 'name,pooja_category,status\nGanapati Puja,Daily & Common Household Poojas,active\nSatyanarayana Vratam,Daily & Common Household Poojas,active',
    }
    
    if entity_type not in samples:
        return JsonResponse({'error': 'Invalid entity type'}, status=400)
    
    response = HttpResponse(samples[entity_type], content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{entity_type}_sample.csv"'
    return response


@login_required
@admin_required
@require_http_methods(["POST"])
def toggle_status(request, entity_type, entity_id):
    """
    Toggle status (ACTIVE/INACTIVE) for a master data entity.
    
    Args:
        entity_type: One of 'city', 'mandal', 'local_area', 'pooja_category', 'pooja'
        entity_id: ID of the entity
    """
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Only Super Admins can toggle status'}, status=403)
    
    model_map = {
        'city': City,
        'mandal': Mandal,
        'local_area': LocalArea,
        'pooja_category': PoojaCategory,
        'pooja': Pooja,
    }
    
    if entity_type not in model_map:
        return JsonResponse({'error': 'Invalid entity type'}, status=400)
    
    try:
        model = model_map[entity_type]
        entity = model.objects.get(id=entity_id)
        
        # Toggle status
        if entity.status == model.STATUS_ACTIVE:
            entity.status = model.STATUS_INACTIVE
            entity.is_active = False
        else:
            entity.status = model.STATUS_ACTIVE
            entity.is_active = True
        
        entity.save(update_fields=['status', 'is_active', 'updated_at'])
        
        messages.success(request, f'{entity_type.title()} status updated to {entity.status}.')
        return JsonResponse({'success': True, 'new_status': entity.status})
        
    except model.DoesNotExist:
        return JsonResponse({'error': 'Entity not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
