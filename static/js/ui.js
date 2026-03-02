/* 
    Phase 3 - Module 5 - Task 5.UI.8 & 5.UI.13
    Dashboard UI JavaScript - UI interactions only
    NO analytics emission, NO data computation, NO event tracking
    Charts consume backend-provided data only
    
    ANALYTICS BOUNDARY: This file must NEVER emit analytics events.
    Analytics ingestion exists only in Module 14 backend.
    UI is analytics-consumer only.
*/

// Chart initialization (using Chart.js if available)
// This is UI-only - no analytics, no computation
document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts if Chart.js is available and chart data exists
    const chartContainers = document.querySelectorAll('.chart-wrapper');
    
    chartContainers.forEach(function(container) {
        const canvas = container.querySelector('canvas');
        if (canvas && typeof Chart !== 'undefined') {
            // Chart data is provided by backend via data attribute or global variable
            const chartId = canvas.id.replace('chart-canvas-', '');
            const chartDataElement = document.getElementById('chart-data-' + chartId);
            
            if (chartDataElement) {
                try {
                    const chartData = JSON.parse(chartDataElement.textContent);
                    
                    // Render chart using backend-provided data
                    // NO transformations, NO aggregations, NO computations
                    new Chart(canvas, {
                        type: chartData.type || 'line',
                        data: chartData.data || {},
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            // UI interactions only - no analytics
                            plugins: {
                                tooltip: {
                                    enabled: true
                                },
                                legend: {
                                    display: true
                                }
                            }
                        }
                    });
                } catch (e) {
                    console.error('Chart rendering error:', e);
                    // Display error message - no retry logic
                    // Use textContent instead of innerHTML to prevent XSS
                    const errorMsg = document.createElement('p');
                    errorMsg.className = 'text-muted text-center';
                    errorMsg.textContent = 'Chart data unavailable.';
                    container.textContent = ''; // Clear container
                    container.appendChild(errorMsg);
                }
            }
        }
    });
    
    // Responsive chart resizing
    window.addEventListener('resize', function() {
        // Charts will auto-resize if Chart.js is configured for responsive mode
        // No manual resizing logic needed
    });
});

// Trust Tooltip Initialization - Task 10.UI.5 & 10.UI.13
// Tooltips are passive UI only - NO analytics emission
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips for trust badges
    const trustTooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (trustTooltipElements.length > 0 && typeof bootstrap !== 'undefined') {
        trustTooltipElements.forEach(function(element) {
            new bootstrap.Tooltip(element, {
                trigger: 'hover focus',
                html: false
            });
        });
    }
    // NOTE: Tooltip initialization is UI-only. No click tracking, no analytics events, no engagement nudging. Analytics belongs to Module 14.
});

/* 
    NOTE: This file does NOT:
    - Emit analytics events
    - Track user interactions
    - Compute or aggregate data
    - Transform chart data
    - Store or cache data
    - Track trust badge clicks or hovers
    
    This is UI interactions only.
    Analytics comes only from Module 14 backend.
    Trust tooltips are passive - no analytics emission (Task 10.UI.13)
*/

// Multi-level Dropdown Support for Poojas Navigation
// Phase 3 - Navbar Enhancement
document.addEventListener('DOMContentLoaded', function() {
    // Handle dropdown submenu on hover (desktop) and click (mobile)
    const dropdownSubmenus = document.querySelectorAll('.dropdown-submenu');
    
    dropdownSubmenus.forEach(function(submenu) {
        const toggle = submenu.querySelector('.dropdown-toggle');
        const menu = submenu.querySelector('.dropdown-menu');
        
        if (toggle && menu) {
            // Desktop: hover to show
            if (window.innerWidth > 991) {
                submenu.addEventListener('mouseenter', function() {
                    menu.classList.add('show');
                });
                
                submenu.addEventListener('mouseleave', function() {
                    menu.classList.remove('show');
                });
            } else {
                // Mobile: click to toggle
                toggle.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    menu.classList.toggle('show');
                });
            }
        }
    });
    
    // Keep parent dropdown open when hovering over submenu
    const poojasDropdown = document.getElementById('poojasDropdown');
    if (poojasDropdown) {
        const parentDropdown = poojasDropdown.closest('.dropdown');
        if (parentDropdown) {
            parentDropdown.addEventListener('mouseenter', function() {
                const menu = parentDropdown.querySelector('.dropdown-menu');
                if (menu) {
                    menu.classList.add('show');
                }
            });
            
            parentDropdown.addEventListener('mouseleave', function() {
                const menu = parentDropdown.querySelector('.dropdown-menu');
                if (menu) {
                    menu.classList.remove('show');
                }
            });
        }
    }
});

