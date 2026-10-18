const formPrefix = 'items'

const orderForm = document.getElementById('order-form')
const formSet = document.getElementById(`${formPrefix}_form_set`)
const formRow = document.getElementsByClassName(`${formPrefix}_form-row`)
const emptyForm = document.getElementById(`${formPrefix}_empty_form`).firstElementChild

const orderTotalField = document.getElementById('order-total')
const orderProductCountField = document.getElementById('order-product-count')

const totalForms = document.getElementById(`id_${formPrefix}-TOTAL_FORMS`)

let formCount = totalForms.value
const formIdRegex = new RegExp(`(${formPrefix}-)(?:__prefix__|\\d+)(-)`, 'g')
let orderTotal = Number(orderTotalField.textContent)

const donationInputField = document.getElementById('id_donation')
let donationAmount = Number(donationInputField.value) || 0
donationInputField.oninput = function () {
  recalculateCart()
}

function nudgeDonation () {
  if (donationAmount === 0) {
    const donationRoundUpModal = new bootstrap.Modal(document.getElementById('donation-round-up-modal'), {
      backdrop: 'static',
      keyboard: false,
      focus: true
    })
    let suggestedAmount = orderTotal % 10

    suggestedAmount = (suggestedAmount < 4 ? 5 - suggestedAmount : 10 - suggestedAmount)
    console.log('Suggesting a donation of', suggestedAmount)

    document.getElementById('round-up-amount').textContent = suggestedAmount
    document.getElementById('donation-round-up-input').value = suggestedAmount
    document.getElementById('rounded-order-total').textContent = suggestedAmount + orderTotal

    donationRoundUpModal.show()
  } else {
    orderForm.submit()
  }
}

function updateDonationAndSubmit (newDonationAmount) {
  if (newDonationAmount) {
    donationInputField.value = newDonationAmount
  }
  orderForm.submit()
}

function updateFormSet () {
  let count = 0
  for (const form of formRow) {
    form.innerHTML = form.innerHTML.replace(formIdRegex, `$1${count++}$2`)
  }
}

function recalculateCart () {
  let itemCount = 0
  let total = Number(donationInputField.value) || 0

  for (const product of document.querySelectorAll('.product-quantity')) {
    const productId = product.id.replace(/-quantity$/, '')
    const quantity = Number(product.textContent) || 0
    const subtotalField = document.getElementById(`${productId}-subtotal`)
    const removeButton = document.querySelector(`.product-remove[data-product="${productId}"]`)
    const price = Number(getProductPrice(productId)) || 0
    const subtotal = price * quantity

    subtotalField.value = quantity ? subtotal.toFixed(2) : ''
    removeButton.disabled = quantity === 0
    itemCount += quantity
    total += subtotal
  }

  orderProductCountField.textContent = itemCount
  orderTotalField.textContent = total.toFixed(2)
  orderTotal = total
  donationAmount = Number(donationInputField.value) || 0
}

// Update the visible cart elements from the submitted formset after a failed order
// creation (for example, due to a validation error such as an invalid ZIP code).
function initializeCart () {
  const quantities = new Map()

  for (const form of formRow) {
    const productField = form.querySelector('select[id$=\'-product\']')
    const quantityField = form.querySelector('input[id$=\'-quantity\']')
    const deleteField = form.querySelector('input[id$=\'-DELETE\']')
    const productId = productField.value
    const quantity = Number(quantityField.value)

    if (!productId || !Number.isFinite(quantity) || quantity <= 0 || deleteField.checked) {
      continue
    }

    quantities.set(productId, (quantities.get(productId) || 0) + quantity)
  }

  for (const product of document.querySelectorAll('.product-quantity')) {
    const productId = product.id.replace(/-quantity$/, '')
    const quantity = quantities.get(productId) || 0

    product.textContent = quantity
  }
  recalculateCart()
}

function focusFirstInvalidField () {
  const invalidFields = document.querySelectorAll('#order-form .is-invalid:not([type="hidden"]):not(:disabled)')
  const firstVisibleInvalidField = Array.from(invalidFields).find((field) => field.getClientRects().length > 0)

  if (firstVisibleInvalidField) {
    firstVisibleInvalidField.focus()
  }
}

function searchSelectedProducts (productId) {
  console.log('searchSelectedProducts', productId)
  for (const form of formRow) {
    const productForm = form.querySelector('select[id$=\'-product\']')
    console.log(productForm)
    if (productForm.value === productId) {
      console.log('found it')
      return form
    }
  }
}

function updateQuantities (productId, increment) {
  console.log('updating quantities')
  const productQuantityField = document.getElementById(`${productId}-quantity`)
  const productQuantity = Number(productQuantityField.innerText) + increment

  productQuantityField.innerHTML = productQuantity

  return productQuantity
}

function getProductPrice (productId) {
  console.log('looking up the price for ', productId)
  return document.getElementById(`${productId}-price`).dataset.price
}

function addProduct (element) {
  const productId = element.dataset.product

  console.log('addProduct', productId)

  const productQuantity = updateQuantities(productId, 1)

  const productRow = searchSelectedProducts(productId)
  if (productRow) {
    console.log('Found an existing row', productRow)
    productRow.querySelector('input[id$=\'-quantity\']').value = productQuantity
    productRow.querySelector('input[id$=\'-DELETE\']').checked = false
  } else {
    console.log('adding a new row')
    const newFormRow = emptyForm.cloneNode(true)

    newFormRow.innerHTML = newFormRow.innerHTML.replace(formIdRegex, `$1${formCount}$2`)
    newFormRow.querySelector('select[id$=\'-product\']').value = productId
    formSet.appendChild(newFormRow)
    formCount++
    totalForms.setAttribute('value', formCount)
    element.parentElement.querySelector('.product-remove').disabled = false
  }
  recalculateCart()
}

function removeProduct (element) {
  const productId = element.dataset.product
  console.log('removeProduct', productId)
  const productQuantity = updateQuantities(productId, -1)
  const productRow = searchSelectedProducts(productId)

  if (productQuantity === 0) {
    element.parentElement.querySelector('.product-remove').disabled = true
    console.log('Product Row', productRow)
    if (productRow.querySelector('input[id$=\'-id\']').value) {
      console.log('Marking the OrderItem for deletion')
      productRow.querySelector('input[id$=\'-DELETE\']').checked = true
    } else {
      console.log('Deleting the row', productRow)

      productRow.remove()
      updateFormSet()

      formCount--
      totalForms.setAttribute('value', formCount)
    }
  } else {
    productRow.querySelector('input[id$=\'-quantity\']').value = productQuantity
  }
  recalculateCart()
}

initializeCart()
focusFirstInvalidField()

function updateOrder (target, orderId, field) {
  const status = target.checked
  let action = 'mark_'

  if (status) {
    action += field
  } else {
    action += 'un' + field
  }

  fetch(update_url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({
      orderId,
      action
    })
  })

    .then((response) => {
      return response.json()
    })

    .then((data) => {
      console.log('data: ', data)
      location.reload()
    })
}
