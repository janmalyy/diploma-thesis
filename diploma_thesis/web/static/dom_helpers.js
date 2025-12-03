export function showError(errorEl, successEl, message) {
  errorEl.textContent = message;
  errorEl.style.display = "block";
  successEl.style.display = "none";
}

export function showSuccess(successEl, errorEl, message) {
  successEl.textContent = message;
  successEl.style.display = "block";
  errorEl.style.display = "none";
}

export function hideMessages(errorEl, successEl) {
  errorEl.style.display = "none";
  successEl.style.display = "none";
}

export function showModal(modalInstance, modalBodyEl, text) {
  modalBodyEl.textContent = text;
  modalInstance.show();
}
