const formPrefix = "items"

const orderForm = document.getElementById("order-form")
const formSet = document.getElementById(`${formPrefix}_form_set`)
const formRow = document.getElementsByClassName(`${formPrefix}_form-row`)
const emptyForm = document.getElementById(`${formPrefix}_empty_form`).firstElementChild

const orderTotalField = document.getElementById("order-total")
const orderProductCountField = document.getElementById("order-product-count")

const totalForms = document.getElementById(`id_${formPrefix}-TOTAL_FORMS`)

let formCount = totalForms.value;
let formIdRegex = new RegExp(`(${formPrefix}-)(?:__prefix__|\\d+)(-)`, "g")
let orderTotal = Number(orderTotalField.textContent)

const donationInputField = document.getElementById("id_donation")
let donationAmount = Number(donationInputField.value)
donationInputField.oninput = function () {
    let donationAmountDelta = Number(donationInputField.value) - donationAmount
    orderTotalField.textContent = Number(orderTotalField.textContent) + donationAmountDelta
    donationAmount = Number(donationInputField.value)
}


function nudgeDonation() {
    if (donationAmount === 0) {
        const donationRoundUpModal = new bootstrap.Modal(document.getElementById("donation-round-up-modal"), {
            backdrop: "static",
            keyboard: false,
            focus: true
        })
        let suggestedAmount = orderTotal % 10;

        suggestedAmount = (suggestedAmount < 4 ? 5 - suggestedAmount : 10 - suggestedAmount)
        console.log("Suggesting a donation of", suggestedAmount)

        document.getElementById("round-up-amount").textContent = suggestedAmount
        document.getElementById("donation-round-up-input").value = suggestedAmount
        document.getElementById("rounded-order-total").textContent = suggestedAmount + orderTotal

        donationRoundUpModal.show()

    } else {
        orderForm.submit();
    }
}


function updateDonationAndSubmit(newDonationAmount) {
    if (newDonationAmount) {
        donationInputField.value = newDonationAmount
    }
    orderForm.submit();
}


function updateFormSet() {
    let count = 0;
    for (let form of formRow) {
        form.innerHTML = form.innerHTML.replace(formIdRegex, `$1${count++}$2`)
    }
}


function searchSelectedProducts(productId) {
    console.log("searchSelectedProducts", productId)
    for (let form of formRow) {
        let productForm = form.querySelector(`select[id$='-product']`)
        console.log(productForm)
        if (productForm.value === productId) {
            console.log("found it")
            return form
        }
    }
}


function updatePricing(productId, increment) {
    console.log("order total", orderTotal)

    const productSubTotalField = document.getElementById(`${productId}-subtotal`)
    let productPrice = getProductPrice(productId)
    let currentTotal = orderTotal
    let productSubTotal = productSubTotalField.value

    console.log("current total", currentTotal)

    if (increment >= 1) {
        orderTotal = currentTotal + Number(productPrice);
        productSubTotal = Number(productSubTotal) + Number(productPrice);
    } else if (increment < 0) {
        orderTotal = currentTotal - Number(productPrice);
        productSubTotal = Number(productSubTotal) - Number(productPrice);
    }
    console.log("New order total", orderTotal)
    orderTotalField.innerText = orderTotal.toFixed(2);
    if (productSubTotal <= 0) {
        productSubTotalField.value = ""
        productSubTotalField.removeAttribute("value")
    } else {
        productSubTotalField.value = productSubTotal.toFixed(2)
    }

    return {currentTotal, productSubTotal};
}


function updateQuantities(productId, increment) {
    console.log("updating quantities")
    const productQuantityField = document.getElementById(`${productId}-quantity`)
    let orderProductCount = Number(orderProductCountField.innerText) + increment;
    let productQuantity = Number(productQuantityField.innerText) + increment;

    orderProductCountField.innerText = orderProductCount;
    productQuantityField.innerHTML = productQuantity;

    return {orderProductCount, productQuantity};
}


function getProductPrice(productId) {
    console.log("looking up the price for ", productId)
    return document.getElementById(`${productId}-price`).innerText
}


function addProduct(element) {
    let productId = element.dataset.product

    console.log("addProduct", productId)

    let pricing = updatePricing(productId, 1)
    let quantities = updateQuantities(productId, 1)

    let productRow = searchSelectedProducts(productId)
    if (productRow) {
        console.log("Found an existing row", productRow)
        productRow.querySelector(`input[id$='-quantity']`).value = quantities.productQuantity
        productRow.querySelector(`input[id$='-DELETE']`).checked = false
    } else {
        console.log("adding a new row")
        const newFormRow = emptyForm.cloneNode(true);

        newFormRow.innerHTML = newFormRow.innerHTML.replace(formIdRegex, `$1${formCount}$2`);
        newFormRow.querySelector(`select[id$='-product']`).value = productId;
        formSet.appendChild(newFormRow);
        formCount++
        totalForms.setAttribute('value', formCount);
        element.parentElement.querySelector('.product-remove').disabled = false;
    }
}


function removeProduct(element) {
    let productId = element.dataset.product
    console.log("removeProduct", productId)
    let pricing = updatePricing(productId, -1)
    let quantities = updateQuantities(productId, -1)
    let productRow = searchSelectedProducts(productId)

    if (quantities.productQuantity === 0) {
        element.parentElement.querySelector('.product-remove').disabled = true;
        console.log("Product Row", productRow)
        if (productRow.querySelector(`input[id$='-id']`).value) {
            console.log("Marking the OrderItem for deletion")
            productRow.querySelector(`input[id$='-DELETE']`).checked = true
        } else {
            console.log("Deleting the row", productRow)

            productRow.remove();
            updateFormSet();

            formCount--;
            totalForms.setAttribute('value', formCount);
        }

    } else {
        productRow.querySelector(`input[id$='-quantity']`).value = quantities.productQuantity
    }
}


function updateDatePaid(target) {
    const datePaidInput = document.getElementById("id_date_paid")
    let paidStatus = target.checked

    if (paidStatus) {
        console.log("marking as paid")
        datePaidInput.value = new Date().toISOString()
    } else {
        console.log("marking as not paid")
        datePaidInput.value = ""
    }
}
