document.querySelectorAll("[data-sortable-report-table]").forEach((table) => {
  table.tHead.rows[0].querySelectorAll("th").forEach((header) => {
    header.addEventListener("click", () => {
      Array.from(table.tBodies[0].rows)
        .sort((firstRow, secondRow) =>
          firstRow.cells[header.cellIndex].textContent.localeCompare(
            secondRow.cells[header.cellIndex].textContent,
            undefined,
            { numeric: true },
          ),
        )
        .forEach((row) => table.tBodies[0].appendChild(row));
    });
  });
});
