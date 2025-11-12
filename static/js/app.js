// Global JavaScript utilities

// Global upload state
let currentUploadTaskId = null;
let uploadInProgress = false;

// Prevent accidental page refresh during upload
window.addEventListener('beforeunload', function(e) {
    if (uploadInProgress) {
        e.preventDefault();
        e.returnValue = 'Upload in progress. Are you sure you want to leave?';
        return e.returnValue;
    }
});

// Cancel upload function
function cancelUpload() {
    if (!currentUploadTaskId) return;
    
    fetch(`/api/cancel-upload/${currentUploadTaskId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        showToast('Upload cancelled', 'warning');
        uploadInProgress = false;
        currentUploadTaskId = null;
        
        // Hide progress and show upload form
        const progressSection = document.getElementById('progressSection');
        const uploadSection = document.getElementById('uploadSection');
        const cancelBtn = document.getElementById('cancelUploadBtn');
        
        if (progressSection) progressSection.style.display = 'none';
        if (uploadSection) uploadSection.style.display = 'block';
        if (cancelBtn) cancelBtn.style.display = 'none';
    })
    .catch(error => {
        console.error('Cancel error:', error);
        showToast('Failed to cancel upload', 'danger');
    });
}

// Show toast notifications
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

// Format date for display
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Handle API errors consistently
function handleApiError(error, defaultMessage = 'An error occurred') {
    console.error('API Error:', error);
    
    if (error.detail) {
        showToast(error.detail, 'danger');
    } else if (error.message) {
        showToast(error.message, 'danger');
    } else {
        showToast(defaultMessage, 'danger');
    }
}

// Set active navigation item
document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
    
    // Check for ongoing uploads on page load
    const storedTaskId = localStorage.getItem('uploadTaskId');
    if (storedTaskId) {
        checkUploadStatus(storedTaskId);
    }
});

// Check upload status and resume if needed
function checkUploadStatus(taskId) {
    fetch(`/api/task-status/${taskId}`)
    .then(response => {
        if (response.ok) {
            return response.json();
        }
        throw new Error('Task not found');
    })
    .then(status => {
        if (status.state === 'PROGRESS') {
            currentUploadTaskId = taskId;
            uploadInProgress = true;
            // Resume progress tracking if on upload page
            if (window.location.pathname === '/') {
                resumeProgressTracking(taskId);
            }
        } else {
            localStorage.removeItem('uploadTaskId');
        }
    })
    .catch(() => {
        localStorage.removeItem('uploadTaskId');
    });
}

// Resume progress tracking
function resumeProgressTracking(taskId) {
    const progressSection = document.getElementById('progressSection');
    const uploadSection = document.getElementById('uploadSection');
    const cancelBtn = document.getElementById('cancelUploadBtn');
    
    if (progressSection) progressSection.style.display = 'block';
    if (uploadSection) uploadSection.style.display = 'none';
    if (cancelBtn) cancelBtn.style.display = 'inline-block';
    
    // Start polling for progress
    pollProgress(taskId);
}

// Store task ID in localStorage for persistence
function storeUploadTask(taskId) {
    localStorage.setItem('uploadTaskId', taskId);
    currentUploadTaskId = taskId;
    uploadInProgress = true;
}

// Clear stored task
function clearUploadTask() {
    localStorage.removeItem('uploadTaskId');
    currentUploadTaskId = null;
    uploadInProgress = false;
}