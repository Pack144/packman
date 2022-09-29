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
