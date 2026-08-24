// Prevent Double Submits on all forms
document.querySelectorAll('form').forEach(form => {
	form.addEventListener('submit', (e) => {
		// Prevent if already submitting
		if (form.classList.contains('is-submitting')) {
			e.preventDefault();
		}

		// Add class to hook our visual indicator on
		form.classList.add('is-submitting');
	});
});

// The PackMate promo has nothing left to offer once the app is on the device.
// It renders visible so it survives with JavaScript off; we take it away here.
const packmatePromo = document.getElementById('packmate-promo');
if (packmatePromo) {
	let installed = false;
	try {
		// install.js sets this from `appinstalled` and from standalone launches,
		// which is the only signal iOS ever gives us.
		installed = localStorage.getItem('packman:installed') === '1';
	} catch {
		// Private browsing blocks storage; keep offering the app.
	}

	// The manifest's scope is "/", so these pages open inside the installed app too.
	const standalone =
		window.matchMedia('(display-mode: standalone)').matches ||
		window.navigator.standalone === true;

	if (installed || standalone) {
		packmatePromo.hidden = true;
	}
}
