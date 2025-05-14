// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    // Flash message handling
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.remove();
            }, 300);
        }, 5000);
    });

    // Modal fix implementation
    const fixModals = function() {
        // Remove any existing modal backdrop to prevent stacking
        const oldBackdrops = document.querySelectorAll('.modal-backdrop');
        oldBackdrops.forEach(backdrop => backdrop.remove());
        
        // Prevent body from shifting
        document.body.style.paddingRight = '0';
        
        // Initialize Bootstrap modals properly
        const modalButtons = document.querySelectorAll('[data-bs-toggle="modal"]');
        modalButtons.forEach(function(button) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Get target modal
                const targetId = button.getAttribute('data-bs-target');
                const modalEl = document.querySelector(targetId);
                
                if (modalEl) {
                    // Create new modal instance each time
                    const modal = new bootstrap.Modal(modalEl, {
                        backdrop: 'static',
                        keyboard: false
                    });
                    
                    // Show the modal
                    modal.show();
                    
                    // Ensure modal is properly positioned
                    modalEl.style.display = 'block';
                    
                    // Apply fixed positioning to prevent scrolling issues
                    document.body.classList.add('modal-open');
                    document.body.style.overflow = 'hidden';
                    document.body.style.paddingRight = '0px';
                    
                    // Add event listener to close button
                    const closeButton = modalEl.querySelector('.btn-close, [data-bs-dismiss="modal"]');
                    if (closeButton) {
                        closeButton.addEventListener('click', function() {
                            modal.hide();
                            document.body.classList.remove('modal-open');
                            document.body.style.overflow = '';
                            document.body.style.paddingRight = '';
                            
                            // Remove backdrop
                            const backdrops = document.querySelectorAll('.modal-backdrop');
                            backdrops.forEach(backdrop => backdrop.remove());
                        });
                    }
                }
            });
        });
    };
    
    // Run modal fix on page load
    fixModals();
    
    // Rerun modal fix if content changes (for dynamically added modals)
    const observer = new MutationObserver(fixModals);
    observer.observe(document.body, { childList: true, subtree: true });
}); 