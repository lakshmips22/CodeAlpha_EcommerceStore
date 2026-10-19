/* Cart state and prices are owned by Django; these forms only submit actions. */
document.addEventListener('submit', (event) => {
    const form = event.target.closest('form[data-cart-form]');
    if (!form || form.dataset.submitting === 'true') return;

    const submitter = event.submitter;
    if (submitter && submitter.name && submitter.value) {
        const action = document.createElement('input');
        action.type = 'hidden';
        action.name = submitter.name;
        action.value = submitter.value;
        form.append(action);
    }

    form.dataset.submitting = 'true';
    if (submitter) submitter.disabled = true;
}, true);
