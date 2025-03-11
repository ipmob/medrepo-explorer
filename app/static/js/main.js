document.addEventListener('DOMContentLoaded', () => {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const fileName = document.getElementById('file-name');
    const uploadButton = document.getElementById('upload-button');
    const uploadForm = document.getElementById('upload-form');
    const uploadStatus = document.getElementById('upload-status');

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);

    // Handle file input change
    fileInput.addEventListener('change', handleFiles);

    // Handle form submission
    uploadForm.addEventListener('submit', handleSubmit);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        dropArea.classList.add('highlight');
    }

    function unhighlight() {
        dropArea.classList.remove('highlight');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    function handleFiles(e) {
        let files;
        if (e.dataTransfer) {
            files = e.dataTransfer.files;
        } else if (e.target && e.target.files) {
            files = e.target.files;
        } else {
            files = e;
        }

        if (files.length > 0) {
            const file = files[0];
            if (file.type === 'application/pdf') {
                fileName.textContent = file.name;
                uploadButton.disabled = false;
                uploadStatus.textContent = '';
                uploadStatus.className = 'upload-status';
            } else {
                fileName.textContent = 'Please select a PDF file';
                uploadButton.disabled = true;
                uploadStatus.textContent = 'Error: Only PDF files are supported';
                uploadStatus.className = 'upload-status error';
            }
        }
    }

    async function handleSubmit(e) {
        e.preventDefault();
        
        if (fileInput.files.length === 0) {
            uploadStatus.textContent = 'Please select a file first';
            uploadStatus.className = 'upload-status error';
            return;
        }

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        uploadButton.disabled = true;
        uploadButton.textContent = 'Uploading...';
        uploadStatus.textContent = 'Uploading and analyzing your file. This may take a moment...';
        uploadStatus.className = 'upload-status';

        try {
            const response = await fetch('/api/upload/', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Upload failed');
            }

            const data = await response.json();
            uploadStatus.textContent = 'File uploaded and analyzed successfully!';
            uploadStatus.className = 'upload-status success';
            
            // Redirect to results page or display results
            // window.location.href = `/results/${data.id}`;
            console.log('Upload response:', data);
            
        } catch (error) {
            console.error('Upload error:', error);
            uploadStatus.textContent = `Error: ${error.message}`;
            uploadStatus.className = 'upload-status error';
        } finally {
            uploadButton.disabled = false;
            uploadButton.textContent = 'Upload & Analyze';
        }
    }
}); 