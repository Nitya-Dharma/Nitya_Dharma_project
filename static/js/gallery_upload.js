/**
 * Gallery Multi-Upload JavaScript
 * Supports drag & drop, 20 images max, client-side validation
 */

(function() {
    'use strict';
    
    const MAX_IMAGES = 20;
    
    // Get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    function getCSRFToken() {
        return getCookie('csrftoken');
    }
    
    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        const uploadModal = document.getElementById('uploadGalleryModal');
        if (!uploadModal) return;
        
        const fileInput = document.getElementById('gallery_images');
        const dropZone = document.getElementById('galleryDropZone');
        const fileCounter = document.getElementById('fileCounter');
        const fileList = document.getElementById('fileList');
        const uploadForm = document.getElementById('galleryUploadForm');
        const submitBtn = uploadForm?.querySelector('button[type="submit"]');
        
        let selectedFiles = [];
        
        // Update counter
        function updateCounter() {
            if (fileCounter) {
                fileCounter.textContent = `${selectedFiles.length} / ${MAX_IMAGES} selected`;
                fileCounter.style.color = selectedFiles.length > MAX_IMAGES ? '#DC2626' : '#64748B';
            }
        }
        
        // Update file list display
        function updateFileList() {
            if (!fileList) return;
            
            fileList.innerHTML = '';
            
            if (selectedFiles.length === 0) {
                fileList.innerHTML = '<p class="text-muted small mb-0">No files selected</p>';
                return;
            }
            
            selectedFiles.forEach((file, index) => {
                const fileItem = document.createElement('div');
                fileItem.className = 'd-flex align-items-center justify-content-between mb-2 p-2 border rounded';
                fileItem.innerHTML = `
                    <div class="d-flex align-items-center gap-2">
                        <i class="bi bi-file-image text-primary"></i>
                        <span class="small">${file.name}</span>
                        <span class="text-muted small">(${(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-secondary gallery-remove-file" data-index="${index}" title="Remove this file" aria-label="Remove ${file.name}">
                        <i class="bi bi-trash"></i> Remove
                    </button>
                `;
                
                // Remove file handler
                fileItem.querySelector('button').addEventListener('click', function() {
                    selectedFiles.splice(index, 1);
                    updateFileInput();
                    updateCounter();
                    updateFileList();
                });
                
                fileList.appendChild(fileItem);
            });
        }
        
        // Update file input
        function updateFileInput() {
            if (!fileInput) return;
            
            const dataTransfer = new DataTransfer();
            selectedFiles.forEach(file => {
                dataTransfer.items.add(file);
            });
            fileInput.files = dataTransfer.files;
        }
        
        // Validate files
        function validateFiles(files) {
            const errors = [];
            const validFiles = [];
            
            Array.from(files).forEach(file => {
                // Check file type
                if (!file.type.startsWith('image/')) {
                    errors.push(`${file.name}: Not an image file`);
                    return;
                }
                
                // Check file size (max 25MB per file; must match FILE_UPLOAD_MAX_IMAGE_BYTES)
                const maxBytes = 25 * 1024 * 1024;
                if (file.size > maxBytes) {
                    errors.push(`${file.name}: File too large (max 25MB)`);
                    return;
                }
                
                validFiles.push(file);
            });
            
            // Check total count
            if (selectedFiles.length + validFiles.length > MAX_IMAGES) {
                errors.push(`Maximum ${MAX_IMAGES} images allowed. You selected ${selectedFiles.length + validFiles.length}`);
            }
            
            return { validFiles, errors };
        }
        
        // Handle file selection
        function handleFiles(files) {
            const { validFiles, errors } = validateFiles(files);
            
            if (errors.length > 0) {
                alert('Validation errors:\n' + errors.join('\n'));
            }
            
            // Add valid files (up to max)
            const remaining = MAX_IMAGES - selectedFiles.length;
            selectedFiles.push(...validFiles.slice(0, remaining));
            
            updateFileInput();
            updateCounter();
            updateFileList();
        }
        
        // File input change (fires when user selects file(s) in picker)
        if (fileInput) {
            fileInput.addEventListener('change', function(e) {
                const files = e.target.files;
                if (files && files.length) {
                    handleFiles(files);
                }
            });
        }
        
        // Drag & drop handlers
        if (dropZone) {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, preventDefaults, false);
            });
            
            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            dropZone.addEventListener('dragenter', function() {
                dropZone.classList.add('drag-over');
            });
            
            dropZone.addEventListener('dragleave', function() {
                dropZone.classList.remove('drag-over');
            });
            
            dropZone.addEventListener('drop', function(e) {
                dropZone.classList.remove('drag-over');
                const files = e.dataTransfer.files;
                handleFiles(files);
            });
        }
        
        // Form submission
        if (uploadForm) {
            uploadForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                if (selectedFiles.length === 0) {
                    alert('Please select at least one image');
                    return;
                }
                
                if (selectedFiles.length > MAX_IMAGES) {
                    alert(`Maximum ${MAX_IMAGES} images allowed`);
                    return;
                }
                
                // Disable submit button
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...';
                }
                
                // Create FormData
                const formData = new FormData();
                selectedFiles.forEach(file => {
                    formData.append('images', file);
                });
                formData.append('caption', document.getElementById('gallery_caption')?.value || '');
                formData.append('csrfmiddlewaretoken', getCSRFToken());
                
                // Submit via AJAX
                fetch(uploadForm.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': getCSRFToken(),
                    },
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Close modal
                        const modal = bootstrap.Modal.getInstance(uploadModal);
                        if (modal) modal.hide();
                        
                        // Reset form
                        selectedFiles = [];
                        updateFileInput();
                        updateCounter();
                        updateFileList();
                        if (uploadForm) uploadForm.reset();
                        
                        // Reload gallery
                        location.reload();
                    } else {
                        alert(data.error || 'Upload failed');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred during upload');
                })
                .finally(() => {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '<i class="bi bi-cloud-upload me-2"></i>Upload Images';
                    }
                });
            });
        }
        
        // Reset on modal close
        uploadModal.addEventListener('hidden.bs.modal', function() {
            selectedFiles = [];
            updateFileInput();
            updateCounter();
            updateFileList();
            if (uploadForm) uploadForm.reset();
        });
        
        // Initial counter update
        updateCounter();
        updateFileList();
    });
})();















