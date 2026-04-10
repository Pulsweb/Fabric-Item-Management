// ─────────────────────────────────────────────────────────────
//  Fabric Agent Wizard — app.js
// ─────────────────────────────────────────────────────────────

const TOTAL_STEPS = 5;
let currentStep = 1;

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  buildStepsIndicator();
  // Wizard starts hidden — welcome screen is shown first
  bindRadioCards();
  bindCapacityToggle();
  bindAdminToggle();
});

// ── Welcome screen ────────────────────────────────────────────
function startWizard(itemType) {
  if (itemType !== 'dataAgent') return; // guard — only dataAgent available
  document.getElementById('welcome').classList.add('hidden');
  document.getElementById('wizard').classList.remove('hidden');
  updateUI();
}

// ── Step indicator dots ───────────────────────────────────────
function buildStepsIndicator() {
  const container = document.getElementById('stepsIndicator');
  const labels = ['Workspace', 'Capacity', 'Agent', 'Admin', 'Review'];
  container.innerHTML = '';
  for (let i = 1; i <= TOTAL_STEPS; i++) {
    const dot = document.createElement('div');
    dot.className = 'step-dot';
    dot.id = `dot-${i}`;
    dot.setAttribute('aria-label', `Step ${i}: ${labels[i - 1]}`);
    dot.innerHTML = `<span class="dot-circle">${i}</span><span class="dot-label">${labels[i - 1]}</span>`;
    container.appendChild(dot);
  }
}

// ── Navigation ────────────────────────────────────────────────
function navigate(direction) {
  if (direction === 1 && !validateStep(currentStep)) return;

  // Skip step 2 (capacity) if reusing existing workspace
  const wsMode = document.querySelector('input[name="workspace_mode"]:checked')?.value;
  if (direction === 1 && currentStep === 1 && wsMode === 'existing') {
    currentStep = 3; // jump over capacity
  } else if (direction === -1 && currentStep === 3 && wsMode === 'existing') {
    currentStep = 1;
  } else {
    currentStep += direction;
  }

  currentStep = Math.max(1, Math.min(TOTAL_STEPS, currentStep));
  updateUI();
}

function updateUI() {
  // Show/hide steps
  document.querySelectorAll('.step').forEach(s => s.classList.add('hidden'));
  const active = document.getElementById(`step-${currentStep}`);
  if (active) active.classList.remove('hidden');

  // Progress bar
  const pct = ((currentStep - 1) / (TOTAL_STEPS - 1)) * 100;
  document.getElementById('progressFill').style.width = `${pct}%`;

  // Dots
  for (let i = 1; i <= TOTAL_STEPS; i++) {
    const dot = document.getElementById(`dot-${i}`);
    dot.classList.toggle('active', i === currentStep);
    dot.classList.toggle('done', i < currentStep);
  }

  // Buttons
  document.getElementById('btnBack').disabled = currentStep === 1;
  const btnNext = document.getElementById('btnNext');
  if (currentStep === TOTAL_STEPS) {
    btnNext.textContent = '🚀 Deploy';
    btnNext.onclick = submitWizard;
  } else {
    btnNext.textContent = 'Next →';
    btnNext.onclick = () => navigate(1);
  }

  // Step counter
  document.getElementById('stepCounter').textContent = `Step ${currentStep} / ${TOTAL_STEPS}`;

  // Build summary on last step
  if (currentStep === TOTAL_STEPS) buildSummary();
}

// ── Validation ────────────────────────────────────────────────
function validateStep(step) {
  clearErrors();
  switch (step) {
    case 1: {
      const mode = document.querySelector('input[name="workspace_mode"]:checked');
      const name = document.getElementById('workspace_name').value.trim();
      if (!mode) return showError('workspace_name', 'Please select a workspace option.');
      if (!name) return showError('workspace_name', 'Workspace name is required.');
      return true;
    }
    case 2: {
      const mode = document.querySelector('input[name="capacity_mode"]:checked');
      if (!mode) return showError('capacity_name', 'Please select a capacity option.');
      if (mode.value === 'yes') {
        const cap = document.getElementById('capacity_name').value.trim();
        if (!cap) return showError('capacity_name', 'Capacity name is required.');
      }
      return true;
    }
    case 3: {
      const name = document.getElementById('agent_name').value.trim();
      if (!name) return showError('agent_name', 'Agent name is required.');
      return true;
    }
    case 4: {
      const mode = document.querySelector('input[name="admin_mode"]:checked');
      if (!mode) return showError('admin_user_object_id', 'Please select an option.');
      if (mode.value === 'yes') {
        const user = document.getElementById('admin_user_object_id').value.trim();
        if (!user) return showError('admin_user_object_id', 'UPN or Object ID is required.');
      }
      return true;
    }
    case 5: {
      const url = document.getElementById('webhookUrl').value.trim();
      if (!url) return showError('webhookUrl', 'Webhook URL is required.');
      try { new URL(url); } catch { return showError('webhookUrl', 'The URL is not valid.'); }
      return true;
    }
    default:
      return true;
  }
}

function showError(fieldId, msg) {
  const field = document.getElementById(fieldId);
  if (field) {
    field.classList.add('error');
    const hint = field.parentElement.querySelector('.field-hint') || createHint(field);
    hint.textContent = msg;
    hint.classList.add('error-msg');
    field.focus();
  }
  return false;
}

function createHint(field) {
  const span = document.createElement('span');
  span.className = 'field-hint';
  field.after(span);
  return span;
}

function clearErrors() {
  document.querySelectorAll('.error').forEach(el => el.classList.remove('error', 'error-msg'));
}

// ── Radio card visual feedback ────────────────────────────────
function bindRadioCards() {
  document.querySelectorAll('.card input[type="radio"]').forEach(radio => {
    radio.addEventListener('change', () => {
      const name = radio.name;
      document.querySelectorAll(`.card input[name="${name}"]`).forEach(r => {
        r.closest('.card').classList.toggle('selected', r.checked);
      });
    });
  });
}

// ── Capacity field toggle ─────────────────────────────────────
function bindCapacityToggle() {
  document.querySelectorAll('input[name="capacity_mode"]').forEach(r => {
    r.addEventListener('change', () => {
      const show = r.value === 'yes' && r.checked;
      document.getElementById('field-capacity-name').classList.toggle('hidden', !show);
    });
  });
}

// ── Admin field toggle ────────────────────────────────────────
function bindAdminToggle() {
  document.querySelectorAll('input[name="admin_mode"]').forEach(r => {
    r.addEventListener('change', () => {
      const show = r.value === 'yes' && r.checked;
      document.getElementById('field-admin-user').classList.toggle('hidden', !show);
    });
  });
}

// ── Workspace hint ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input[name="workspace_mode"]').forEach(r => {
    r.addEventListener('change', () => {
      const hint = document.getElementById('workspace-hint');
      if (r.value === 'new' && r.checked) {
        hint.textContent = 'This workspace will be created if it does not already exist.';
      } else if (r.value === 'existing' && r.checked) {
        hint.textContent = 'The Managed Identity must be a member of this workspace to detect it.';
      }
    });
  });
});

// ── Summary ───────────────────────────────────────────────────
function buildSummary() {
  const wsMode = document.querySelector('input[name="workspace_mode"]:checked')?.value;
  const capMode = document.querySelector('input[name="capacity_mode"]:checked')?.value;
  const adminMode = document.querySelector('input[name="admin_mode"]:checked')?.value;

  const rows = [
    { label: 'Workspace', value: document.getElementById('workspace_name').value.trim() },
    { label: 'Workspace mode', value: wsMode === 'new' ? 'Create if not existing' : 'Reuse existing' },
  ];

  if (wsMode === 'new') {
    rows.push({
      label: 'Capacity',
      value: capMode === 'yes'
        ? document.getElementById('capacity_name').value.trim()
        : 'None (Trial/Shared)',
    });
  }

  rows.push(
    { label: 'Agent name', value: document.getElementById('agent_name').value.trim() },
    { label: 'Description', value: document.getElementById('agent_description').value.trim() || '—' },
    {
      label: 'Administrator',
      value: adminMode === 'yes'
        ? document.getElementById('admin_user_object_id').value.trim()
        : '—',
    },
  );

  const grid = document.getElementById('summaryGrid');
  grid.innerHTML = rows.map(r => `
    <div class="summary-row">
      <span class="summary-label">${r.label}</span>
      <span class="summary-value">${escapeHtml(r.value)}</span>
    </div>
  `).join('');
}

// ── Submit ────────────────────────────────────────────────────
async function submitWizard() {
  if (!validateStep(TOTAL_STEPS)) return;

  const webhookUrl = document.getElementById('webhookUrl').value.trim();
  const wsMode  = document.querySelector('input[name="workspace_mode"]:checked')?.value;
  const capMode = document.querySelector('input[name="capacity_mode"]:checked')?.value;
  const adminMode = document.querySelector('input[name="admin_mode"]:checked')?.value;

  const payload = {
    workspace_name:       document.getElementById('workspace_name').value.trim(),
    agent_name:           document.getElementById('agent_name').value.trim(),
    agent_description:    document.getElementById('agent_description').value.trim(),
    capacity_name:        (wsMode === 'new' && capMode === 'yes')
                            ? document.getElementById('capacity_name').value.trim()
                            : '',
    admin_user_object_id: (adminMode === 'yes')
                            ? document.getElementById('admin_user_object_id').value.trim()
                            : '',
  };

  // Hide wizard, show loading
  document.querySelector('main').classList.add('hidden');
  document.querySelector('.wizard-footer').classList.add('hidden');
  const resultPanel = document.getElementById('resultPanel');
  resultPanel.classList.remove('hidden');
  setResult('loading', '⏳', 'Deployment in progress…', 'The Azure Automation runbook has been triggered. This may take a few seconds.');

  try {
    // Azure Automation webhooks do not return CORS headers.
    // Using mode:'no-cors' + Content-Type:'text/plain' avoids the CORS preflight
    // and sends the request as a simple POST. The response is opaque (unreadable)
    // but the webhook is reliably triggered server-side.
    await fetch(webhookUrl, {
      method: 'POST',
      mode: 'no-cors',
      headers: { 'Content-Type': 'text/plain' },
      body: JSON.stringify(payload),
    });

    setResult('success', '✅', 'Deployment triggered!',
      `The runbook has been triggered with the following parameters:<br><br>
      <strong>Workspace:</strong> ${escapeHtml(payload.workspace_name)}<br>
      <strong>Agent:</strong> ${escapeHtml(payload.agent_name)}<br><br>
      Check your <strong>Automation Account → Jobs</strong> in the Azure Portal to track execution.`
    );
  } catch (err) {
    setResult('error', '❌', 'Connection error',
      `Unable to send the request.<br><code>${escapeHtml(err.message)}</code><br><br>
      Verify that the webhook URL is correct and that your network can reach <code>*.azure-automation.net</code>.`
    );
  }
}

function setResult(type, icon, title, body) {
  const panel = document.getElementById('resultPanel');
  panel.className = `result-panel result-${type}`;
  document.getElementById('resultIcon').textContent = icon;
  document.getElementById('resultTitle').textContent = title;
  document.getElementById('resultBody').innerHTML = body;
}

// ── Reset ─────────────────────────────────────────────────────
function resetWizard() {
  currentStep = 1;
  document.querySelectorAll('input[type="text"], input[type="url"], textarea').forEach(el => el.value = '');
  document.querySelectorAll('input[type="radio"]').forEach(el => el.checked = false);
  document.querySelectorAll('.card').forEach(c => c.classList.remove('selected'));
  document.getElementById('field-capacity-name').classList.add('hidden');
  document.getElementById('field-admin-user').classList.add('hidden');
  document.querySelector('main').classList.remove('hidden');
  document.querySelector('.wizard-footer').classList.remove('hidden');
  document.getElementById('resultPanel').classList.add('hidden');
  // Return to welcome screen
  document.getElementById('wizard').classList.add('hidden');
  document.getElementById('welcome').classList.remove('hidden');
}

// ── Utils ─────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
