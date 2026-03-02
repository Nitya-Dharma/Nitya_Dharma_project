/**
 * Follow System JavaScript
 * Handles follow/unfollow functionality for pandits and temples
 */

(function() {
    'use strict';
    
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
    
    // Update CSRF token in fetch requests
    function getCSRFToken() {
        return getCookie('csrftoken');
    }
    
    // Follow/Unfollow handler
    function handleFollow(entityType, entityPublicId, button) {
        const isFollowing = button.classList.contains('following');
        const action = isFollowing ? 'unfollow' : 'follow';
        const url = `/${action}/${entityType}/${entityPublicId}/`;
        
        // Set loading state
        button.classList.add('loading');
        button.disabled = true;
        
        const csrfToken = getCSRFToken();
        if (!csrfToken) {
            alert('CSRF token not found. Please refresh the page and try again.');
            button.classList.remove('loading');
            button.disabled = false;
            return;
        }
        
        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
            },
            credentials: 'same-origin',
        })
        .then(response => {
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                // Server returned HTML (likely a 404 page) instead of JSON
                throw new Error(`Server returned ${response.status} ${response.statusText}. Please check the URL.`);
            }
            
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
                });
            }
            return response.json();
        })
        .then(data => {
            button.classList.remove('loading');
            button.disabled = false;
            
            if (data.success) {
                // Toggle following state
                if (data.is_following) {
                    button.classList.add('following');
                    button.classList.remove('not-following');
                    // Update text - CSS will add checkmark via ::after
                    const textSpan = button.querySelector('.follow-text');
                    if (textSpan) {
                        textSpan.textContent = 'Following';
                    } else {
                        button.textContent = 'Following';
                    }
                } else {
                    button.classList.remove('following');
                    button.classList.add('not-following');
                    const textSpan = button.querySelector('.follow-text');
                    if (textSpan) {
                        textSpan.textContent = 'Follow';
                    } else {
                        button.textContent = 'Follow';
                    }
                }
                
                // Update follower count if element exists
                const countElement = document.querySelector('.follower-count');
                if (countElement && data.follower_count !== undefined) {
                    countElement.textContent = `(${data.follower_count} followers)`;
                }
            } else {
                alert(data.error || 'An error occurred');
            }
        })
        .catch(error => {
            button.classList.remove('loading');
            button.disabled = false;
            console.error('Follow error:', error);
            alert(error.message || 'An error occurred. Please try again.');
        });
    }
    
    // Check follow status on page load
    function checkFollowStatus(entityType, entityPublicId, button) {
        const url = `/follow/status/${entityType}/${entityPublicId}/`;
        
        fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
        })
        .then(response => {
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                // Server returned HTML instead of JSON - likely not logged in or 404
                console.debug('Follow status check: non-JSON response (expected if not logged in)');
                return null;
            }
            
            if (!response.ok) {
                // Non-200 response - log but don't show error to user
                console.warn('Follow status check failed:', response.status);
                return null;
            }
            return response.json();
        })
        .then(data => {
            if (!data) return; // Error case handled above
            
            if (data.is_following) {
                button.classList.add('following');
                button.classList.remove('not-following');
                // CSS will add checkmark via ::after
                const textSpan = button.querySelector('.follow-text');
                if (textSpan) {
                    textSpan.textContent = 'Following';
                } else {
                    button.textContent = 'Following';
                }
            } else {
                button.classList.remove('following');
                button.classList.add('not-following');
            }
            
            // Update follower count if element exists
            const countElement = document.querySelector('.follower-count');
            if (countElement && data.follower_count !== undefined) {
                countElement.textContent = `(${data.follower_count} followers)`;
            }
        })
        .catch(error => {
            // Silently fail - user might not be logged in
            console.debug('Follow status check error (expected if not logged in):', error);
        });
    }
    
    // Initialize follow buttons when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        // Find all follow buttons (only those that are not disabled)
        const followButtons = document.querySelectorAll('.follow-btn[data-entity-type][data-entity-public-id]:not(.disabled):not([disabled])');
        
        followButtons.forEach(button => {
            const entityType = button.getAttribute('data-entity-type');
            const entityPublicId = button.getAttribute('data-entity-public-id');
            
            if (!entityType || !entityPublicId) {
                console.warn('Follow button missing required data attributes:', button);
                return;
            }
            
            // Check follow status on load (only if user is authenticated)
            // The check_follow_status endpoint handles unauthenticated users gracefully
            checkFollowStatus(entityType, entityPublicId, button);
            
            // Add click handler
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                // Prevent double-clicks
                if (button.classList.contains('loading') || button.disabled) {
                    return;
                }
                
                handleFollow(entityType, entityPublicId, button);
            });
        });
    });
})();

