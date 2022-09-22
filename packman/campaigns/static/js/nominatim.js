const api_url = 'https://nominatim.openstreetmap.org/reverse'
let place_id

function constructGpsQueryURL (position) {
  const query_url = new URL(api_url)
  query_url.searchParams.set('format', 'jsonv2')
  query_url.searchParams.set('lat', position.coords.latitude)
  query_url.searchParams.set('lon', position.coords.longitude)
  console.log('Query URL: ' + query_url)
  return query_url
}

async function queryApi (position) {
  const response = await fetch(constructGpsQueryURL(position))
  const data = await response.json()
  if (response) {
    place_id = data.place_id
  }
  return data
}

function show (data) {
  console.log(data)
}

const x = document.getElementById('location-feedback')
const address_input = document.getElementById('id_address')
address_input.onfocus = function () {
  if (place_id == null) {
    getLocation()
  }
}

function getLocation () {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(recordPosition, showError)
  } else {
    x.innerHTML = 'Geolocation is not supported by this browser.'
  }
}

function showPosition (position) {
  x.innerHTML = 'Latitude: ' + position.coords.latitude +
        '<br>Longitude: ' + position.coords.longitude
}

function recordPosition (position) {
  const latitude_input = document.getElementById('id_latitude')
  const longitude_input = document.getElementById('id_longitude')
  const gps_accuracy_input = document.getElementById('id_gps_accuracy')
  latitude_input.value = position.coords.latitude
  longitude_input.value = position.coords.longitude
  gps_accuracy_input.value = position.coords.accuracy
  resolvePosition(position)
}

async function resolvePosition (position) {
  const address_input = document.getElementById('id_address')
  const city_input = document.getElementById('id_city')
  const state_input = document.getElementById('id_state')
  const zipcode_input = document.getElementById('id_zipcode')
  const results = await queryApi(position)
  console.log(results)
  if (results) {
    address_input.value = results.address.house_number + ' ' + results.address.road
    city_input.value = results.address.city
    zipcode_input.value = results.address.postcode
    for (let i = 0; i < state_input.options.length; i++) {
      if (state_input.options[i].text === results.address.state) { state_input.selectedIndex = i }
    }
  }
}

function showError (error) {
  switch (error.code) {
    case error.PERMISSION_DENIED:
      x.innerHTML = 'User denied the request for geolocation.'
      break
    case error.POSITION_UNAVAILABLE:
      x.innerHTML = 'Location information is unavailable.'
      break
    case error.TIMEOUT:
      x.innerHTML = 'The request to get user location timed out.'
      break
    case error.UNKNOWN_ERROR:
      x.innerHTML = 'An unknown error occurred.'
      break
  }
}
