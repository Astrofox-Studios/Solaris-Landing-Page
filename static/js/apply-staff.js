(function () {
    var form = document.getElementById('staff-form');
    var steps = Array.from(document.querySelectorAll('.apply-form-step'));
    var dots = Array.from(document.querySelectorAll('.apply-steps-indicator .apply-step-dot'));
    var lines = Array.from(document.querySelectorAll('.apply-steps-indicator .apply-step-line'));
    var currentStep = 1;

    // ── Number input enhancement ──────────────────────────────────────────
    function enhanceNumberInputs() {
        document.querySelectorAll('.apply-field input[type="number"]').forEach(function (input) {
            var wrap = document.createElement('div');
            wrap.className = 'number-input-wrap';
            input.parentNode.insertBefore(wrap, input);
            wrap.appendChild(input);

            var up = document.createElement('button');
            up.type = 'button';
            up.className = 'num-btn num-up';
            up.setAttribute('aria-label', 'Increase');
            up.innerHTML = '<i class="fa-solid fa-chevron-up"></i>';

            var down = document.createElement('button');
            down.type = 'button';
            down.className = 'num-btn num-down';
            down.setAttribute('aria-label', 'Decrease');
            down.innerHTML = '<i class="fa-solid fa-chevron-down"></i>';

            wrap.appendChild(up);
            wrap.appendChild(down);

            up.addEventListener('click', function () {
                var max = parseInt(input.max) || 999;
                var val = parseInt(input.value) || 0;
                if (val < max) { input.value = val + 1; input.dispatchEvent(new Event('input')); }
            });
            down.addEventListener('click', function () {
                var min = parseInt(input.min) || 0;
                var val = parseInt(input.value) || 0;
                if (val > min) { input.value = val - 1; input.dispatchEvent(new Event('input')); }
            });
        });
    }

    enhanceNumberInputs();

    // ── Step nav ──────────────────────────────────────────────────────────
    function showStep(n, goingBack) {
        steps.forEach(function (s) { s.classList.remove('active', 'going-back'); });
        var target = steps.find(function (s) { return parseInt(s.dataset.step) === n; });
        if (!target) return;
        if (goingBack) target.classList.add('going-back');
        target.classList.add('active');
        currentStep = n;
        updateIndicator();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function updateIndicator() {
        dots.forEach(function (dot, i) {
            var stepNum = i + 1;
            dot.classList.remove('active', 'done');
            if (stepNum < currentStep) dot.classList.add('done');
            else if (stepNum === currentStep) dot.classList.add('active');
        });
        lines.forEach(function (line, i) {
            line.classList.toggle('done', i + 1 < currentStep);
        });
    }

    // ── Role selection ────────────────────────────────────────────────────
    var roleCards = Array.from(document.querySelectorAll('.role-card'));
    var nextBtn1 = document.getElementById('step1-next');

    roleCards.forEach(function (card) {
        card.addEventListener('click', function () {
            card.querySelector('input[type="radio"]').checked = true;
            nextBtn1.disabled = false;
        });
    });

    // Step 1 -> 2
    if (nextBtn1) {
        nextBtn1.addEventListener('click', function () {
            var selected = form.querySelector('input[name="role"]:checked');
            if (!selected) return;
            var role = selected.value;

            document.querySelectorAll('.role-fields').forEach(function (rf) { rf.classList.remove('active'); });
            var target = document.querySelector('.role-fields[data-role="' + role + '"]');
            if (target) target.classList.add('active');

            document.getElementById('step2-title').textContent = role + ' Application';
            showStep(2);
        });
    }

    // Step 2 -> 3
    var nextBtn2 = document.getElementById('step2-next');
    if (nextBtn2) {
        nextBtn2.addEventListener('click', function () {
            var activeFields = document.querySelector('.role-fields.active');
            var textInputs = activeFields ? activeFields.querySelectorAll('input[type="text"][required], textarea[required]') : [];
            var firstEmpty = null;
            textInputs.forEach(function (el) {
                if (!el.value.trim() && !firstEmpty) firstEmpty = el;
            });
            if (firstEmpty) { firstEmpty.focus(); return; }

            var langBoxes = activeFields ? activeFields.querySelectorAll('input[name="languages"]') : [];
            if (langBoxes.length > 0 && !Array.from(langBoxes).some(function (cb) { return cb.checked; })) {
                var wrap = langBoxes[0].closest('.apply-checkboxes');
                if (wrap) { wrap.style.outline = '2px solid var(--accent-warm)'; setTimeout(function () { wrap.style.outline = ''; }, 2000); }
                return;
            }

            var radioGroups = activeFields ? activeFields.querySelectorAll('[type="radio"][required]') : [];
            if (radioGroups.length > 0) {
                var names = [...new Set(Array.from(radioGroups).map(function (r) { return r.name; }))];
                for (var i = 0; i < names.length; i++) {
                    if (!activeFields.querySelector('[name="' + names[i] + '"]:checked')) {
                        var firstRadio = activeFields.querySelector('[name="' + names[i] + '"]');
                        if (firstRadio) firstRadio.closest('.apply-radio-group').scrollIntoView({ behavior: 'smooth' });
                        return;
                    }
                }
            }

            showStep(3);
        });
    }

    // Step 3 -> 4 (populate review)
    var nextBtn3 = document.getElementById('step3-next');
    if (nextBtn3) {
        nextBtn3.addEventListener('click', function () {
            var discord = form.querySelector('[name="discord"]');
            var age = form.querySelector('[name="age"]');
            var mic = form.querySelector('[name="microphone"]:checked');

            if (!discord || !discord.value.trim()) { discord && discord.focus(); return; }
            if (!age || !age.value.trim()) { age && age.focus(); return; }
            if (!mic) {
                var micField = form.querySelector('[name="microphone"]');
                micField && micField.closest('.apply-field').scrollIntoView({ behavior: 'smooth' });
                return;
            }

            populateReview();
            showStep(4);
        });
    }

    function populateReview() {
        var role = (form.querySelector('input[name="role"]:checked') || {}).value || '';
        var activeFields = document.querySelector('.role-fields.active');

        function setRow(id, value, rowId) {
            var el = document.getElementById(id);
            if (el) el.textContent = value || '';
            if (rowId) {
                var row = document.getElementById(rowId);
                if (row) row.style.display = value ? '' : 'none';
            }
        }

        setRow('review-role', role);

        // Experience
        var exp = activeFields ? activeFields.querySelector('[name="experience"]') : null;
        setRow('review-experience', exp ? exp.value.trim() : '');

        // GitHub (developer)
        var github = form.querySelector('[name="github"]');
        setRow('review-github', github ? github.value.trim() : '', 'review-row-github');

        // Languages (developer)
        var langs = Array.from(form.querySelectorAll('[name="languages"]:checked')).map(function (cb) { return cb.value; });
        setRow('review-languages', langs.length ? langs.join(', ') : '', 'review-row-languages');

        // Role-specific extras (varies by role)
        var extraLabel = '';
        var extraValue = '';
        if (role === 'Builder') {
            var style = form.querySelector('[name="style"]');
            var yrs = form.querySelector('[name="years_building"]');
            extraLabel = 'Building experience';
            extraValue = [yrs ? yrs.value.trim() : '', style ? style.value.trim() : ''].filter(Boolean).join(', ');
        } else if (role === 'Support Staff / Moderator') {
            var yrs = form.querySelector('[name="years_support"]');
            extraLabel = 'Experience length';
            extraValue = yrs ? yrs.value.trim() : '';
        } else if (role === 'System Administrator') {
            var yrs = form.querySelector('[name="years_sysadmin"]');
            extraLabel = 'Experience length';
            extraValue = yrs ? yrs.value.trim() : '';
        } else if (role === '2D Artist') {
            var artType = form.querySelector('[name="art_type"]');
            var yrs = form.querySelector('[name="years_art"]');
            extraLabel = 'Art type / experience';
            extraValue = [artType ? artType.value.trim() : '', yrs ? yrs.value.trim() : ''].filter(Boolean).join(', ');
        } else if (role === '3D Modeler') {
            var modelType = form.querySelector('[name="model_type"]');
            var software = form.querySelector('[name="software"]');
            extraLabel = 'Model type / software';
            extraValue = [modelType ? modelType.value.trim() : '', software ? software.value.trim() : ''].filter(Boolean).join(', ');
        } else if (role === 'Game / Content Designer') {
            var fav = form.querySelector('[name="fav_aspect"]');
            var yrs = form.querySelector('[name="years_design"]');
            extraLabel = 'Favourite aspect / experience';
            extraValue = [fav ? fav.value.trim() : '', yrs ? yrs.value.trim() : ''].filter(Boolean).join(', ');
        } else if (role === 'Animator') {
            var animType = form.querySelector('[name="anim_type"]:checked');
            var yrs = form.querySelector('[name="years_animating"]');
            extraLabel = 'Animation type / experience';
            extraValue = [animType ? animType.value : '', yrs ? yrs.value.trim() : ''].filter(Boolean).join(', ');
        } else if (role === 'Marketing') {
            var yrs = form.querySelector('[name="years_marketing"]');
            var best = form.querySelector('[name="best_method"]');
            extraLabel = 'Experience / method';
            extraValue = [yrs ? yrs.value.trim() : '', best ? best.value.trim() : ''].filter(Boolean).join(', ');
        } else if (role === 'Other') {
            var customRole = form.querySelector('[name="custom_role"]');
            extraLabel = 'Custom role';
            extraValue = customRole ? customRole.value.trim() : '';
        } else if (role === 'Java / Kotlin Developer') {
            var yrs = form.querySelector('[name="years_coding"]');
            extraLabel = 'Coding experience';
            extraValue = yrs ? yrs.value.trim() : '';
        }

        var extraLabelEl = document.getElementById('review-roleextra-label');
        if (extraLabelEl) extraLabelEl.textContent = extraLabel;
        setRow('review-roleextra', extraValue, 'review-row-roleextra');

        // General
        var discord = form.querySelector('[name="discord"]');
        var age = form.querySelector('[name="age"]');
        var mic = form.querySelector('[name="microphone"]:checked');
        var socials = form.querySelector('[name="socials"]');
        var portfolio = form.querySelector('[name="portfolio_link"]');

        setRow('review-discord', discord ? discord.value.trim() : '');
        setRow('review-age', age ? age.value.trim() : '');
        setRow('review-mic', mic ? mic.value : '');
        setRow('review-socials', socials ? socials.value.trim() : '', 'review-row-socials');
        setRow('review-portfolio', portfolio ? portfolio.value.trim() : '', 'review-row-portfolio');
    }

    // Prev buttons
    document.querySelectorAll('.apply-prev-btn').forEach(function (btn) {
        btn.addEventListener('click', function () { showStep(currentStep - 1, true); });
    });

    // Submit
    form.addEventListener('submit', function (e) {
        e.preventDefault();
        var submitBtn = document.getElementById('submit-btn');
        var errorEl = document.getElementById('apply-error');
        errorEl.style.display = 'none';

        submitBtn.classList.add('loading');
        submitBtn.querySelector('i').className = 'fa-solid fa-spinner';

        fetch('/apply/staff', { method: 'POST', body: new FormData(form) })
            .then(function (r) { return r.json(); })
            .then(function (json) {
                if (json.success) {
                    document.getElementById('success-app-id').textContent = '#' + json.id;
                    form.querySelectorAll('.apply-form-step').forEach(function (s) { s.style.display = 'none'; });
                    document.querySelector('.apply-steps-indicator').style.display = 'none';
                    document.getElementById('apply-success').style.display = 'block';
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                } else {
                    var msgs = { invalid_role: 'Please select a valid role.', missing_required: 'Please fill in all required fields.', server_error: 'Something went wrong on our end. Please try again.' };
                    errorEl.textContent = msgs[json.error] || 'An error occurred. Please try again.';
                    errorEl.style.display = 'block';
                    submitBtn.classList.remove('loading');
                    submitBtn.querySelector('i').className = 'fa-solid fa-paper-plane';
                }
            })
            .catch(function () {
                errorEl.textContent = 'Network error. Please check your connection and try again.';
                errorEl.style.display = 'block';
                submitBtn.classList.remove('loading');
                submitBtn.querySelector('i').className = 'fa-solid fa-paper-plane';
            });
    });
})();
