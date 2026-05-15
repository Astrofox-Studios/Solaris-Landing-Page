(function () {
    var form = document.getElementById('tester-form');
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

    // ── Skill slider ──────────────────────────────────────────────────────
    var slider = document.getElementById('t-skill');
    var skillVal = document.getElementById('skill-val');
    if (slider) {
        slider.addEventListener('input', function () { skillVal.textContent = slider.value; });
    }

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
        lines.forEach(function (line, i) { line.classList.toggle('done', i + 1 < currentStep); });
    }

    // Step 1 -> 2: rules check
    var nextBtn1 = document.getElementById('step1-next');
    if (nextBtn1) {
        nextBtn1.addEventListener('click', function () {
            var rulesOk = form.querySelector('[name="rules_agreed"]:checked');
            var blacklistOk = form.querySelector('[name="blacklist_agreed"]:checked');
            var ownsJava = form.querySelector('[name="owns_java"]:checked');
            var warning = document.getElementById('rules-warning');

            if (!rulesOk || rulesOk.value !== 'yes' || !blacklistOk || blacklistOk.value !== 'yes' || !ownsJava || ownsJava.value !== 'yes') {
                warning.style.display = 'block';
                return;
            }
            warning.style.display = 'none';
            showStep(2);
        });
    }

    // Step 2 -> 3
    var nextBtn2 = document.getElementById('step2-next');
    if (nextBtn2) {
        nextBtn2.addEventListener('click', function () {
            var fields = ['email', 'minecraft_ign', 'discord', 'age', 'pronouns'].map(function (n) { return form.querySelector('[name="' + n + '"]'); });
            var firstEmpty = fields.find(function (f) { return f && !f.value.trim(); });
            if (firstEmpty) { firstEmpty.focus(); return; }

            var feedbackOk = form.querySelector('[name="feedback_ok"]:checked');
            if (!feedbackOk || feedbackOk.value !== 'yes') {
                var fbField = form.querySelector('[name="feedback_ok"]');
                fbField && fbField.closest('.apply-field').scrollIntoView({ behavior: 'smooth' });
                return;
            }
            showStep(3);
        });
    }

    // Step 3 -> 4
    var nextBtn3 = document.getElementById('step3-next');
    if (nextBtn3) {
        nextBtn3.addEventListener('click', function () {
            var prior = form.querySelector('[name="prior_testing"]');
            var otherExp = form.querySelector('[name="other_experience"]');
            var opinion = form.querySelector('[name="opinion"]');

            if (!prior || !prior.value.trim()) { prior && prior.focus(); return; }
            if (!otherExp || !otherExp.value.trim()) { otherExp && otherExp.focus(); return; }
            if (!opinion || !opinion.value.trim()) { opinion && opinion.focus(); return; }

            populateReview();
            showStep(4);
        });
    }

    function populateReview() {
        function val(name) {
            var el = form.querySelector('[name="' + name + '"]');
            return el ? el.value.trim() : '';
        }
        function checkedVal(name) {
            var el = form.querySelector('[name="' + name + '"]:checked');
            return el ? el.value : '';
        }
        function setEl(id, value) {
            var el = document.getElementById(id);
            if (el) el.textContent = value || '';
        }

        setEl('review-ign', val('minecraft_ign'));
        setEl('review-email', val('email'));
        setEl('review-discord', val('discord'));
        setEl('review-age', val('age'));
        setEl('review-pronouns', val('pronouns'));
        setEl('review-skill', val('skill_level') + ' / 10');
        setEl('review-tested', checkedVal('tested_before') === 'yes' ? 'Yes' : 'No');
        setEl('review-java', checkedVal('owns_java') === 'yes' ? 'Yes' : 'No');
        setEl('review-rules', checkedVal('rules_agreed') === 'yes' && checkedVal('blacklist_agreed') === 'yes' ? 'Agreed' : 'Not agreed');
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

        fetch('/apply/tester', { method: 'POST', body: new FormData(form) })
            .then(function (r) { return r.json(); })
            .then(function (json) {
                if (json.success) {
                    document.getElementById('success-app-id').textContent = '#' + json.id;
                    form.querySelectorAll('.apply-form-step').forEach(function (s) { s.style.display = 'none'; });
                    document.querySelector('.apply-steps-indicator').style.display = 'none';
                    document.getElementById('apply-success').style.display = 'block';
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                } else {
                    var msgs = {
                        invalid_email: 'Please enter a valid email address.',
                        must_agree_rules: 'You must agree to all rules to apply.',
                        must_own_java: 'You must own a valid Minecraft Java account.',
                        must_accept_feedback: 'You must be willing to give feedback.',
                        missing_required: 'Please fill in all required fields.',
                        invalid_skill_level: 'Please select a valid skill level.',
                        server_error: 'Something went wrong on our end. Please try again.',
                    };
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
