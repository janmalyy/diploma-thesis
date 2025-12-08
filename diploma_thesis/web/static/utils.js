/**
 * Extracts all PubMed IDs from a Handsontable sheet and returns
 * a deduplicated flat array of IDs (strings) and
 * per-cell PubMed IDs, skipping the header and cells containing only ".".
 *
 * @param {Handsontable} hotInstance - The Handsontable instance
 * @param {int} pubmedColIndex
 * @returns {{ uniqueIds: string[], cellMap: Record<number, string[]> }}
 */
function extractPubmedIds(hotInstance, pubmedColIndex) {
  if (pubmedColIndex === -1) {
    return { uniqueIds: [], cellMap: {} };
  }

  // Gather all values from the PUBMED column
  const rowCount = hotInstance.countRows();
  const allIds = [];
  const cellMap = {};

  // Start loop at r = 1 to skip the header row (index 0)
  for (let r = 1; r < rowCount; r++) {
    const cellValue = hotInstance.getDataAtCell(r, pubmedColIndex);

    if (!cellValue || typeof cellValue !== "string") continue;

    // Skip cells where the content is exactly "."
    if (cellValue === ".") continue;

    const ids = cellValue
      .split(",")
      .map(id => id.trim())
      .filter(id => id.length > 0);

    if (ids.length > 0) {
      // Store cell IDs using the row index
      cellMap[r] = ids;
      allIds.push(...ids);
    }
  }
  // Deduplicate and return
  const uniqueIds = Array.from(new Set(allIds));

  console.log("Extracted %i unique ids, starting with %s", uniqueIds.length, uniqueIds.slice(0,5));
  return { uniqueIds, cellMap };
}


/**
 * Converts PubMed IDs to hyperlinks by fetching URLs from the API
 * and updating the cells in the Handsontable instance.
 * 
 * @param {Handsontable} hotInstance - The Handsontable instance
 * @param {int} pubmedColIndex - The index of the column containing PubMed IDs
 * @returns {Promise<void>}
 */
export async function batchConvertAndApplyPubmedLinks(hotInstance, pubmedColIndex) {
  const { uniqueIds, cellMap } = extractPubmedIds(hotInstance, pubmedColIndex);

  if (uniqueIds.length === 0) return;

  const response = await fetch("/api/pubmed/convert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids: uniqueIds })
  });

  if (!response.ok) {
    throw new Error("Failed to convert PubMed IDs.");
  }

  if (pubmedColIndex === -1) return;

  const data = await response.json();
  const linkMap = data.result || {};

  // write hyperlinks back
  for (const [row, ids] of Object.entries(cellMap)) {
    const linkedCell = ids
      .map(id =>
        linkMap[id]
          ? `<a href="${linkMap[id]}" target="_blank">${id}</a>`
          : id
      )
      .join(", ");

    hotInstance.setDataAtCell(Number(row), pubmedColIndex, linkedCell);
  }
}
