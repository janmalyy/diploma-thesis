import { batchConvertAndApplyPubmedLinks } from "./utils.js";
import { showError, showSuccess, hideMessages, showModal } from "./dom_helpers.js";

document.addEventListener("DOMContentLoaded", () => {
  // -------------------- DOM Elements --------------------
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

  const sheetSelector = document.getElementById("sheet-selector");

  // -------------------- State --------------------
  let hot;
  let allSheetsData = [];
  let currentSheetName = null;
  let originalFileName = "";
  let pendingFile = null;

  // -------------------- Helpers --------------------
  function createCosmicLinks(value) {
    if (!value) return "";
    return value
      .split(",")
      .map(id => `<a href="https://cancer.sanger.ac.uk/cosmic/search?q=${id.trim()}" target="_blank">${id.trim()}</a>`)
      .join(", ");
  }

  const bgColorRenderer = (instance, td, row, col, prop, value, cellProperties) => {
    Handsontable.renderers.TextRenderer(instance, td, row, col, prop, value, cellProperties);

    if (value === 'Benign') {
     td.style.background = 'rgba(86,177,68,0.85)';
    } else if (value === 'Benign/Likely_benign') {
        td.style.background = 'rgba(181,234,169,0.85)';
      } else if (value === 'Likely_benign') {
        td.style.background = 'rgba(255,233,195,0.85)';
      } else if (value === 'Conflicting_classifications_of_pathogenicity') {
        td.style.background = 'rgba(255,193,87,0.85)';
      }
  };

  Handsontable.renderers.registerRenderer('bgColorRenderer', bgColorRenderer);

  function switchSheet(name) {
    const sheet = allSheetsData.find(s => s.name === name);
    if (!sheet) return;

    // Reset button styles
    Array.from(sheetSelector.children).forEach(btn => {
      btn.classList.remove('btn-primary');
      btn.classList.add('btn-secondary');
    });

    // Highlight the active button
    const activeBtn = sheetSelector.querySelector(`button[data-sheet-name="${name}"]`);
    if (activeBtn) {
      activeBtn.classList.remove('btn-secondary');
      activeBtn.classList.add('btn-primary');
    }

    currentSheetName = name;

    initializeHandsontable(sheet.data);
  }

  function renderSheetSelector(sheetsData) {
    sheetSelector.innerHTML = '';

    if (sheetsData.length <= 1) return; // No need for a selector if only one sheet

    sheetsData.forEach((sheet, index) => {
      const button = document.createElement('button');
      button.className = index === 0 ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-secondary';
      button.textContent = sheet.name;
      button.setAttribute('data-sheet-name', sheet.name);

      button.addEventListener('click', () => {
        if (sheet.name !== currentSheetName) {
          switchSheet(sheet.name);
        }
      });
      sheetSelector.appendChild(button);
    });
  }

  // -------------------- Upload --------------------
  async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    hideMessages(errorMessage, successMessage);

    try {
      const response = await fetch("/api/excel/upload", { method: "POST", body: formData });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Error uploading file");
      }

      const data = await response.json();
      allSheetsData = data.sheets;
      originalFileName = data.filename;

      if (allSheetsData.length === 0) {
        throw new Error("The uploaded file contains no data sheets.");
      }

      const firstSheet = allSheetsData[0];
      currentSheetName = firstSheet.name;

      showSuccess(successMessage, errorMessage, `File "${originalFileName}" uploaded successfully.`);
      currentFileName.textContent = originalFileName;
      editorContainer.style.display = "block";

      renderSheetSelector(allSheetsData);
      initializeHandsontable(firstSheet.data);

    } catch (error) {
      showError(errorMessage, successMessage, error.message);
      editorContainer.style.display = "none";
      sheetSelector.innerHTML = '';
    }
  }

  uploadForm.addEventListener("submit", e => {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) { showError(errorMessage, successMessage, "Please select a file to upload."); return; }

    if (file.name.split(".").pop().toLowerCase() !== "xlsx") {
      showError(errorMessage, successMessage, "Only .xlsx files are supported.");
      return;
    }

    if (allSheetsData.length > 0) {
      pendingFile = file;
      confirmOverwriteModal.show();
    } else { uploadFile(file); }
  });

  confirmOverwriteBtn.addEventListener("click", () => {
    confirmOverwriteModal.hide();
    if (pendingFile) { uploadFile(pendingFile); pendingFile = null; }
  });

  // -------------------- Handsontable --------------------
  function initializeHandsontable(data) {
    if (hot) hot.destroy();

    let cosmicCol = -1, pubmedCol = -1, clinvarSignCol = -1;
    if (data?.length) {
      const headers = data[0];
      cosmicCol = headers.indexOf("COSMIC");
      pubmedCol = headers.indexOf("PUBMED");
      clinvarSignCol = headers.indexOf("clinvar_sig");
    }

    hot = new Handsontable(hotContainer, {
      data,
      rowHeaders: true,
      colHeaders: true,
      contextMenu: {
        items: {
          "generateLLMSummary": {
            name: "Generate LLM summary",
            callback: (_, selection) => {
              const rowIndex = selection[0].start.row;
              const rowId = hot.getDataAtRow(rowIndex)[0];
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
      cells: (row, col) => {
        const cellProps = {};
        if (row === 0) cellProps.className = 'first-row-bold';
        if (cosmicCol !== -1 && col === cosmicCol && row > 0) {
          cellProps.renderer = (_, td, row, col, prop, value) => {
            td.innerHTML = value ? createCosmicLinks(value) : "";
            return td;
          };
        }
        if (pubmedCol !== -1 && col === pubmedCol && row > 0) cellProps.renderer = "html";
        if (clinvarSignCol !== -1 && col === clinvarSignCol && row > 0) cellProps.renderer = "bgColorRenderer";
        return cellProps;
      }
    });

    if (pubmedCol !== -1) {
      batchConvertAndApplyPubmedLinks(hot, pubmedCol)
        .catch(error => { console.error(error); showError(errorMessage, successMessage, "Error converting PubMed IDs: " + error.message); });
    }
  }

  // -------------------- LLM Summary --------------------
  // This logic is simplified; in a multi-sheet application, the API
  // would likely need to know *which sheet* the row_id comes from.
  // For now, it remains unchanged, assuming row_id is globally unique or
  // the backend only processes the current sheet data.
  async function generateLLMSummary(rowId) {
    try {
      const response = await fetch("/api/generate-llm-summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // NOTE: If row IDs are only unique per sheet, you need to send currentSheetName here:
        // body: JSON.stringify({ row_id: rowId, sheet_name: currentSheetName })
        body: JSON.stringify({ row_id: rowId })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Error generating LLM summary");
      }

      const data = await response.json();
      showModal(summaryModal, summaryModalBody, data.result);
    } catch (error) {
      showModal(summaryModal, summaryModalBody, "Error: " + error.message);
    }
  }

  // -------------------- Export --------------------
  async function exportFile(format) {
    // UPDATED: Check for data based on the new state variable
    if (allSheetsData.length === 0) { showError(errorMessage, successMessage, "No data to export."); return; }

    // NOTE: This currently only exports the data currently visible in the HOT instance.
    // To export ALL sheets, you would need to loop through allSheetsData and send
    // it to the backend for re-packaging into a multi-sheet Excel file.

    const data = hot.getData(0, 0, hot.countRows() - 1, hot.countCols() - 1, true);
    // Use the original filename
    const filename = format === "csv" ? originalFileName.replace(".xlsx", ".csv") : originalFileName;
    const contentType = format === "csv" ? "text/csv" : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

    try {
      // NOTE: This API call must be updated on the backend to accept data as
      // an array of sheet objects if you want to export *all* sheets to a multi-sheet Excel file.
      // For now, it sends only the currently visible sheet data.
      const response = await fetch(`/api/excel/export/${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data, filename, current_sheet_name: currentSheetName })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Error exporting file");
      }

      const blob = new Blob([await response.arrayBuffer()], { type: contentType });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showSuccess(successMessage, errorMessage, `File exported successfully as ${format.toUpperCase()}.`);
    } catch (error) {
      showError(errorMessage, successMessage, error.message);
    }
  }

  exportXlsxBtn.addEventListener("click", () => exportFile("xlsx"));
  exportCsvBtn.addEventListener("click", () => exportFile("csv"));
});
