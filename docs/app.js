// resume-ops clean static documentation & .env configurator app.js

document.addEventListener('DOMContentLoaded', () => {
  initEnvBuilder();
  initSnippetTabs();
  initModelFetcher();
});

// Toast notification helper
function showToast(message) {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 2800);
}

// Clipboard copy helper
window.copyText = function (elementId, label) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const text = el.innerText || el.value;
  navigator.clipboard.writeText(text).then(() => {
    showToast(`Copied ${label || 'snippet'} to clipboard!`);
  }).catch(() => {
    showToast('Failed to copy');
  });
};

// Snippet tabs switching
function initSnippetTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn[data-tab]');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const parent = btn.closest('.snippet-box');
      if (!parent) return;
      parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      parent.querySelectorAll('.snippet-pane').forEach(p => p.style.display = 'none');
      
      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.style.display = 'block';
    });
  });
}

// Default models fallback list
const FALLBACK_MODELS = [
  'deepseek/deepseek-v4-pro',
  'anthropic/claude-opus-4-8',
  'anthropic/claude-sonnet-4-5',
  'openai/gpt-4o',
  'openai/gpt-4o-mini',
  'qwen/minimax/minimax-m2.7',
  'qwen/qwen3.6-plus',
  'ibm-granite/granite-4.1-8b'
];

// Model fetcher logic (Queries OpenRouter / custom OPENAI_BASE_URL)
function initModelFetcher() {
  const fetchBtn = document.getElementById('btn-fetch-models');
  if (fetchBtn) {
    fetchBtn.addEventListener('click', fetchModelsFromProvider);
  }
}

async function fetchModelsFromProvider() {
  const baseUrlInput = document.getElementById('env-base-url');
  let baseUrl = baseUrlInput ? baseUrlInput.value.trim() : '';
  if (!baseUrl) {
    baseUrl = 'https://openrouter.ai/api/v1';
  }
  // Normalize base URL
  baseUrl = baseUrl.replace(/\/+$/, '');
  const endpoint = baseUrl.endsWith('/models') ? baseUrl : `${baseUrl}/models`;

  const fetchBtn = document.getElementById('btn-fetch-models');
  if (fetchBtn) fetchBtn.textContent = 'Fetching...';

  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    let modelList = [];
    if (Array.isArray(data.data)) {
      modelList = data.data.map(m => m.id).filter(Boolean);
    } else if (Array.isArray(data)) {
      modelList = data.map(m => m.id || m).filter(Boolean);
    }

    if (modelList.length === 0) {
      throw new Error('No models found in response');
    }

    updateModelSelects(modelList);
    showToast(`Successfully fetched ${modelList.length} models!`);
  } catch (err) {
    console.warn('Model fetch warning:', err);
    showToast(`Could not fetch live models. Loaded default presets.`);
    updateModelSelects(FALLBACK_MODELS);
  } finally {
    if (fetchBtn) fetchBtn.textContent = '⚡ Fetch Models';
  }
}

function updateModelSelects(models) {
  const selectIds = [
    'env-default-model',
    'env-strategy-model',
    'env-work-model',
    'env-skills-model'
  ];

  selectIds.forEach(id => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const currentVal = sel.value;
    sel.innerHTML = '';
    
    const optDefault = document.createElement('option');
    optDefault.value = '';
    optDefault.textContent = id === 'env-default-model' ? '-- Select Default Model --' : '-- Inherit DEFAULT_MODEL --';
    sel.appendChild(optDefault);

    models.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      if (m === currentVal) opt.selected = true;
      sel.appendChild(opt);
    });
  });

  generateEnvOutput();
}

// Interactive .env generator
function initEnvBuilder() {
  const inputs = document.querySelectorAll('.env-input');
  inputs.forEach(input => {
    input.addEventListener('input', generateEnvOutput);
    input.addEventListener('change', generateEnvOutput);
  });
  
  // Populate initial fallback models
  updateModelSelects(FALLBACK_MODELS);
  generateEnvOutput();
}

function generateEnvOutput() {
  const getValue = (id) => {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
  };

  const openaiKey = getValue('env-openai-key');
  const anthropicKey = getValue('env-anthropic-key');
  const geminiKey = getValue('env-gemini-key');
  const baseUrl = getValue('env-base-url');

  const defaultModel = getValue('env-default-model') || 'deepseek/deepseek-v4-pro';
  const strategyModel = getValue('env-strategy-model');
  const workModel = getValue('env-work-model');
  const skillsModel = getValue('env-skills-model');

  const theme = getValue('env-theme') || 'jsonresume-theme-folio';
  const style = getValue('env-style');

  const maxConcurrency = getValue('env-concurrency') || '2';
  const maxRetries = getValue('env-max-retries') || '10';

  let envText = `# ==========================================\n`;
  envText += `# resume-ops Generated Environment File\n`;
  envText += `# ==========================================\n\n`;

  envText += `# Provider Credentials\n`;
  envText += `OPENAI_API_KEY=${openaiKey}\n`;
  envText += `ANTHROPIC_API_KEY=${anthropicKey}\n`;
  envText += `GEMINI_API_KEY=${geminiKey}\n`;
  if (baseUrl) {
    envText += `OPENAI_BASE_URL=${baseUrl}\n`;
  }
  envText += `\n`;

  envText += `# AI Model Routing\n`;
  envText += `DEFAULT_MODEL=${defaultModel}\n`;
  if (strategyModel) envText += `STRATEGY_MODEL=${strategyModel}\n`;
  if (workModel) envText += `WORK_MODEL=${workModel}\n`;
  if (skillsModel) envText += `SKILLS_MODEL=${skillsModel}\n`;
  envText += `\n`;

  envText += `# Themes & Rendering\n`;
  envText += `DEFAULT_THEME=${theme}\n`;
  envText += `ALLOWED_THEMES=["jsonresume-theme-folio", "jsonresume-theme-stackoverflow"]\n\n`;

  envText += `# Tailoring Tone & Style\n`;
  envText += `TAILORING_STYLE=${style}\n\n`;

  envText += `# Environment & Storage\n`;
  envText += `DATA_DIR=/data\n`;
  envText += `MASTER_RESUME_PATH=/data/master-resume.json\n`;
  envText += `LOG_LEVEL=INFO\n\n`;

  envText += `# LLM Throttling & Retries\n`;
  envText += `LLM_MAX_CONCURRENCY=${maxConcurrency}\n`;
  envText += `LLM_MAX_RETRIES=${maxRetries}\n`;
  envText += `LLM_RETRY_MIN_WAIT_SECONDS=3\n`;
  envText += `LLM_RETRY_MAX_WAIT_SECONDS=60\n`;

  const outputEl = document.getElementById('env-code-output');
  if (outputEl) {
    outputEl.textContent = envText;
  }
}
