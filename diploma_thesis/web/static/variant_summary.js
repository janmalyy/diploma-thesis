document.addEventListener('DOMContentLoaded', () => {
    const summaryForm = document.getElementById('summary-form');
    const loadingOverlay = document.getElementById('loading-overlay');
    const resultContainer = document.getElementById('result-container');
    const summaryContent = document.getElementById('summary-content');
    const errorAlert = document.getElementById('error-alert');
    const errorMessage = document.getElementById('error-message');
    const copyBtn = document.getElementById('copy-btn');

    summaryForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Reset state
        errorAlert.style.display = 'none';
        resultContainer.style.display = 'none';
        loadingOverlay.style.display = 'flex';

        const formData = {
            gene: document.getElementById('gene').value.trim(),
            change: document.getElementById('change').value.trim(),
            level: document.getElementById('level').value
        };

        try {
            const response = await fetch('/api/generate-llm-summary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to generate summary');
            }

            // Display result
            summaryContent.textContent = data.result;
            resultContainer.style.display = 'block';
            
            // Scroll to result
            resultContainer.scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            console.error('Error:', error);
            errorMessage.textContent = error.message;
            errorAlert.style.display = 'block';
        } finally {
            loadingOverlay.style.display = 'none';
        }
    });

    copyBtn.addEventListener('click', () => {
        const text = summaryContent.textContent;
        navigator.clipboard.writeText(text).then(() => {
            const originalText = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            copyBtn.classList.replace('btn-outline-light', 'btn-success');
            
            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.classList.replace('btn-success', 'btn-outline-light');
            }, 2000);
        });
    });
});
