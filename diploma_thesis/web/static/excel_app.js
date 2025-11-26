document.addEventListener("DOMContentLoaded", function () {
  const uploadForm = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-input");
  const errorMessage = document.getElementById("error-message");
  const successMessage = document.getElementById("success-message");
  const editorContainer = document.getElementById("editor-container");
  const currentFileName = document.querySelector("#current-file span");
  const exportXlsxBtn = document.getElementById("export-xlsx");
  const exportCsvBtn = document.getElementById("export-csv");
  const hotContainer = document.getElementById("hot-container");
  const confirmOverwriteBtn = document.getElementById("confirmOverwrite");
  const confirmOverwriteModal = new bootstrap.Modal(document.getElementById("confirmOverwriteModal"));

  let hot; // Handsontable instance
  let currentData = null;
  let originalFileName = "";
  let pendingFile = null; // Store the file that's waiting for confirmation

  // Function to upload a file
  function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    // Hide previous messages
    hideMessages();

    // Upload file
    fetch("/api/excel/upload", {
      method: "POST",
      body: formData
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(err => {
          throw new Error(err.detail || "Error uploading file");
        });
      }
      return response.json();
    })
    .then(data => {
      currentData = data.data;
      originalFileName = data.filename;

      // Show success message
      showSuccess(`File "${originalFileName}" uploaded successfully.`);

      // Update UI
      currentFileName.textContent = originalFileName;
      editorContainer.style.display = "block";

      // Initialize or update Handsontable
      initializeHandsontable(currentData);
    })
    .catch(error => {
      showError(error.message);
    });
  }

  // Handle file upload form submission
  uploadForm.addEventListener("submit", function(e) {
    e.preventDefault();

    const file = fileInput.files[0];
    if (!file) {
      showError("Please select a file to upload.");
      return;
    }

    // Check file extension
    const fileExt = file.name.split('.').pop().toLowerCase();
    if (fileExt !== 'xlsx') {
      showError("Only .xlsx files are supported.");
      return;
    }

    // Check if a file is already loaded
    if (currentData !== null) {
      // Store the file for later use
      pendingFile = file;
      // Show confirmation dialog
      confirmOverwriteModal.show();
    } else {
      // No file loaded yet, proceed with upload
      uploadFile(file);
    }
  });

  // Handle confirmation dialog "Overwrite" button
  confirmOverwriteBtn.addEventListener("click", function() {
    // Hide the modal
    confirmOverwriteModal.hide();

    // Proceed with upload if we have a pending file
    if (pendingFile) {
      uploadFile(pendingFile);
      pendingFile = null; // Clear the pending file
    }
  });

  // Initialize Handsontable
  function initializeHandsontable(data) {
    if (hot) {
      hot.destroy();
    }

    // Find the index of the COSMIC column
    let cosmicColumnIndex = -1;
    if (data && data.length > 0) {
      const headers = data[0];
      cosmicColumnIndex = headers.findIndex(header => header === "COSMIC");
    }

    // Function to convert COSMIC IDs to hyperlinks
    function createCosmicLinks(cosmicValue) {
      if (!cosmicValue) return '';

      // Split by comma if multiple IDs exist
      const cosmicIds = cosmicValue.split(',').map(id => id.trim());

      // Convert each ID to a hyperlink
      return cosmicIds.map(id => {
        if (!id) return '';
        return `<a href="https://cancer.sanger.ac.uk/cosmic/search?q=${id}" target="_blank">${id}</a>`;
      }).join(', ');
    }

    hot = new Handsontable(hotContainer, {
      data: data,
      rowHeaders: true,
      colHeaders: true,
      contextMenu: true,
      // TODO calculate custom widths for every column with function
      colWidths: 120,
      manualColumnResize: true,
      manualRowResize: true,
      licenseKey: 'non-commercial-and-evaluation', // Free license for non-commercial use
      stretchH: 'all',
      autoColumnSize: true,
      minSpareRows: 1,
      minSpareCols: 1,
      height: '100%',
      width: '100%',
      filters: true,
      dropdownMenu: true,
      formulas: true,
      fixedRowsTop: 1,

      // Use the 'cells' function to dynamically apply CSS class and cell renderer
      cells(row, col) {
         const cellProperties = {};

         if (row === 0) {
            // Assign a custom CSS class to every cell in the first row (index 0)
            cellProperties.className = 'first-row-bold';
         }

         // Apply custom renderer for COSMIC column
         if (cosmicColumnIndex !== -1 && col === cosmicColumnIndex && row > 0) {
            cellProperties.renderer = function(instance, td, row, col, prop, value, cellProperties) {
              if (value) {
                td.innerHTML = createCosmicLinks(value);
              } else {
                td.innerHTML = '';
              }
              return td;
            };
         }

         return cellProperties;
      }
    });
  }

  // Export as XLSX
  exportXlsxBtn.addEventListener("click", function() {
    if (!currentData) {
      showError("No data to export.");
      return;
    }

    // The last 'true' parameter ensures the data is returned as raw values, not objects.
    const data = hot.getData(0, 0, hot.countRows() - 1, hot.countCols() - 1, true);

    fetch("/api/excel/export/xlsx", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        data: data,
        filename: originalFileName
      })
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(err => {
          throw new Error(err.detail || "Error exporting file");
        });
      }
      // Explicitly handle as blob with correct content type
      return response.arrayBuffer().then(buffer => new Blob([buffer], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      }));
    })
    .then(blob => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = originalFileName;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      showSuccess("File exported successfully as XLSX.");
    })
    .catch(error => {
      showError(error.message);
    });
  });

  // Export as CSV
  exportCsvBtn.addEventListener("click", function() {
    if (!currentData) {
      showError("No data to export.");
      return;
    }

    const data = hot.getData(0, 0, hot.countRows() - 1, hot.countCols() - 1, true);
    const csvFilename = originalFileName.replace('.xlsx', '.csv');

    fetch("/api/excel/export/csv", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        data: data,
        filename: csvFilename
      })
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(err => {
          throw new Error(err.detail || "Error exporting file");
        });
      }
      // Explicitly handle as blob with correct content type
      return response.arrayBuffer().then(buffer => new Blob([buffer], {
        type: "text/csv"
      }));
    })
    .then(blob => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = csvFilename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      showSuccess("File exported successfully as CSV.");
    })
    .catch(error => {
      showError(error.message);
    });
  });

  // Helper functions for showing/hiding messages
  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = "block";
    successMessage.style.display = "none";
  }

  function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.style.display = "block";
    errorMessage.style.display = "none";
  }

  function hideMessages() {
    errorMessage.style.display = "none";
    successMessage.style.display = "none";
  }
});
