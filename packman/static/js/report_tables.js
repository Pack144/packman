function escapeCsvValue(value) {
  return `"${value.replaceAll('"', '""')}"`;
}

document.querySelectorAll("[data-csv-download]").forEach((button) => {
  button.addEventListener("click", () => {
    const table = document.getElementById(button.dataset.csvTableId);
    if (!table) {
      throw new Error(`CSV table not found: ${button.dataset.csvTableId}`);
    }

    const rows = table.querySelectorAll("thead tr, tbody tr");
    const csv = Array.from(rows, (row) =>
      Array.from(row.cells, (cell) => escapeCsvValue(cell.textContent.trim().replaceAll(/\s+/g, " "))).join(","),
    ).join("\r\n");
    const url = URL.createObjectURL(new Blob([`\uFEFF${csv}\r\n`], { type: "text/csv;charset=utf-8" }));
    const download = document.createElement("a");
    download.href = url;
    download.download = button.dataset.csvFilename;
    document.body.appendChild(download);
    download.click();
    download.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  });
});
