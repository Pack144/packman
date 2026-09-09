/**
 * Generic click-to-sort behavior shared by any list of "rows" (table <tr>s,
 * or div/anchor based rows) where each row has a descendant element carrying
 * data-sort-key="<column>" data-sort-value="<value>" for every sortable
 * column, and each clickable column header carries
 * data-sort-header="<column>" plus an onclick calling sortRows().
 *
 * rowSelector should match every row to be reordered (e.g. "#order_rows > a"
 * or "#sales_ordered_table tbody tr"). headerSelector should match every
 * header in the same group, so their aria-sort indicators can be reset
 * before the newly clicked header is marked.
 */
function sortRows (rowSelector, headerSelector, column) {
  const rows = Array.from(document.querySelectorAll(rowSelector))
  if (rows.length === 0) {
    return
  }

  const headers = Array.from(document.querySelectorAll(headerSelector))
  const clickedHeader = headers.find((header) => header.dataset.sortHeader === column)
  const direction = clickedHeader && clickedHeader.getAttribute('aria-sort') === 'ascending' ? 'descending' : 'ascending'

  headers.forEach((header) => header.setAttribute('aria-sort', 'none'))
  if (clickedHeader) {
    clickedHeader.setAttribute('aria-sort', direction)
  }

  const valueOf = (row) => {
    const cell = row.querySelector(`[data-sort-key="${column}"]`)
    const raw = cell ? cell.dataset.sortValue : ''
    const asNumber = Number.parseFloat(raw)
    return Number.isNaN(asNumber) ? raw.toLowerCase() : asNumber
  }

  rows.sort((a, b) => {
    const valueA = valueOf(a)
    const valueB = valueOf(b)
    if (valueA < valueB) {
      return direction === 'ascending' ? -1 : 1
    }
    if (valueA > valueB) {
      return direction === 'ascending' ? 1 : -1
    }
    return 0
  })

  const parent = rows[0].parentNode
  rows.forEach((row) => parent.appendChild(row))
}
