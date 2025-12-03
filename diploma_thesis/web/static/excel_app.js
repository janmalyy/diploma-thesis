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

  const summaryModalEl = document.getElementById("summaryModal");
  const summaryModalBody = document.getElementById("summaryModalBody");
  const summaryModal = new bootstrap.Modal(summaryModalEl);

  let hot; // Handsontable instance
  let currentData = null;
  let originalFileName = "";
  let pendingFile = null; // Store the file that's waiting for confirmation

  // Function to upload a file
  function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    hideMessages();

    fetch("/api/excel/upload", { method: "POST", body: formData })
      .then(response => {
        if (!response.ok) {
          return response.json().then(err => { throw new Error(err.detail || "Error uploading file"); });
        }
        return response.json();
      })
      .then(data => {
        currentData = data.data;
        originalFileName = data.filename;
        showSuccess(`File "${originalFileName}" uploaded successfully.`);
        currentFileName.textContent = originalFileName;
        editorContainer.style.display = "block";
        initializeHandsontable(currentData);
      })
      .catch(error => { showError(error.message); });
  }

  uploadForm.addEventListener("submit", function(e) {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) { showError("Please select a file to upload."); return; }

    const fileExt = file.name.split('.').pop().toLowerCase();
    if (fileExt !== 'xlsx') { showError("Only .xlsx files are supported."); return; }

    if (currentData !== null) {
      pendingFile = file;
      confirmOverwriteModal.show();
    } else { uploadFile(file); }
  });

  confirmOverwriteBtn.addEventListener("click", function() {
    confirmOverwriteModal.hide();
    if (pendingFile) { uploadFile(pendingFile); pendingFile = null; }
  });

  function initializeHandsontable(data) {
    if (hot) hot.destroy();

    let cosmicColumnIndex = -1;
    let pubmedColumnIndex = -1;
    if (data && data.length > 0) {
      const headers = data[0];
      cosmicColumnIndex = headers.findIndex(header => header === "COSMIC");
      pubmedColumnIndex = headers.findIndex(header => header === "PUBMED");
    }

    function createCosmicLinks(cosmicValue) {
      if (!cosmicValue) return '';
      const cosmicIds = cosmicValue.split(',').map(id => id.trim());
      return cosmicIds.map(id => `<a href="https://cancer.sanger.ac.uk/cosmic/search?q=${id}" target="_blank">${id}</a>`).join(', ');
    }

    hot = new Handsontable(hotContainer, {
      data: data,
      rowHeaders: true,
      colHeaders: true,
      contextMenu: {
        items: {
          "generateLLMSummary": {
            name: "Generate LLM summary",
            callback: function(key, selection) {
              const rowIndex = selection[0].start.row;
              const rowId = hot.getDataAtRow(rowIndex)[0]; // Assuming row ID is in the first column
              generateLLMSummary(rowId);
            }
          },
          "sep1": "---------",
	      "copy": {},
          "remove_row": {}
        }
      },
      colWidths: 250,
      manualColumnResize: true,
      manualRowResize: true,
      licenseKey: 'non-commercial-and-evaluation',
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
         if (row === 0) cellProperties.className = 'first-row-bold';
         if (cosmicColumnIndex !== -1 && col === cosmicColumnIndex && row > 0) {
            cellProperties.renderer = function(instance, td, row, col, prop, value) {
              td.innerHTML = value ? createCosmicLinks(value) : '';
              return td;
            };
         }
         if (pubmedColumnIndex !== -1 && col === pubmedColumnIndex && row > 0) {
            cellProperties.renderer = 'html';
         }
         return cellProperties;
      }
    });

    if (pubmedColumnIndex !== -1) {
      try {
        batchConvertAndApplyPubmedLinks(hot, pubmedColumnIndex)
          .catch(error => { console.error(error); showError("Error converting PubMed IDs: " + error.message); });
      } catch (error) { console.error(error); showError("Error processing PubMed IDs: " + error.message); }
    }
  }

  function generateLLMSummary(rowId) {
    fetch("/api/excel/generate-llm-summary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ row_id: rowId })
    })
    .then(response => {
      if (!response.ok) return response.json().then(err => { throw new Error(err.detail || "Error generating LLM summary"); });
      return response.json();
    })
    .then(data => {
      showSummaryModal(data.result);
    })
    .catch(error => {
      showSummaryModal("Error: " + error.message);
    });
  }

  function showSummaryModal(text) {
    summaryModalBody.textContent = text;
    summaryModal.show();
  }

  // Export as XLSX
  exportXlsxBtn.addEventListener("click", function() {
    if (!currentData) { showError("No data to export."); return; }
    const data = hot.getData(0, 0, hot.countRows() - 1, hot.countCols() - 1, true);
    fetch("/api/excel/export/xlsx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: data, filename: originalFileName })
    })
    .then(response => {
      if (!response.ok) return response.json().then(err => { throw new Error(err.detail || "Error exporting file"); });
      return response.arrayBuffer().then(buffer => new Blob([buffer], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
    })
    .then(blob => {
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
    .catch(error => { showError(error.message); });
  });

  // Export as CSV
  exportCsvBtn.addEventListener("click", function() {
    if (!currentData) { showError("No data to export."); return; }
    const data = hot.getData(0, 0, hot.countRows() - 1, hot.countCols() - 1, true);
    const csvFilename = originalFileName.replace('.xlsx', '.csv');
    fetch("/api/excel/export/csv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: data, filename: csvFilename })
    })
    .then(response => {
      if (!response.ok) return response.json().then(err => { throw new Error(err.detail || "Error exporting file"); });
      return response.arrayBuffer().then(buffer => new Blob([buffer], { type: "text/csv" }));
    })
    .then(blob => {
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
    .catch(error => { showError(error.message); });
  });

  function showError(message) { errorMessage.textContent = message; errorMessage.style.display = "block"; successMessage.style.display = "none"; }
  function showSuccess(message) { successMessage.textContent = message; successMessage.style.display = "block"; errorMessage.style.display = "none"; }
  function hideMessages() { errorMessage.style.display = "none"; successMessage.style.display = "none"; }
});
