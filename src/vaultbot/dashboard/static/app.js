/* V.A.U.L.T. BOT — Dashboard SPA */
/* Uses textContent for all user data (XSS prevention). */
/* innerHTML is NEVER used — all DOM construction uses createElement. */

// API_TOKEN is injected by the server into index.html as a global variable

// ===========================
// API Client
// ===========================

var api = {
  request: function(method, path, body) {
    var opts = {
      method: method,
      headers: {
        'Authorization': 'Bearer ' + API_TOKEN,
        'Content-Type': 'application/json',
      },
    };
    if (body !== undefined) {
      opts.body = JSON.stringify(body);
    }
    return fetch('/dashboard/api/' + path, opts).then(function(res) { return res.json(); });
  },
  get: function(path) { return this.request('GET', path); },
  post: function(path, body) { return this.request('POST', path, body); },
  put: function(path, body) { return this.request('PUT', path, body); },
  del: function(path, body) { return this.request('DELETE', path, body); },
};

// ===========================
// Navigation
// ===========================

function navigate(section) {
  document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
  document.getElementById('page-' + section).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(function(n) { n.classList.remove('active'); });
  var navEl = document.querySelector('[data-section="' + section + '"]');
  if (navEl) navEl.classList.add('active');
  if (loaders[section]) loaders[section]();
}

var loaders = {
  dashboard: loadDashboard,
  config: loadConfig,
  platforms: loadPlatforms,
  llm: loadLLM,
  allowlist: loadAllowlist,
  plugins: loadPlugins,
  teams: loadTeams,
  credentials: loadCredentials,
  audit: loadAudit,
};

// ===========================
// Toast Notifications
// ===========================

function toast(msg, type) {
  type = type || 'info';
  var container = document.getElementById('toastContainer');
  var el = document.createElement('div');
  el.className = 'toast toast-' + type;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(function() { el.remove(); }, 3500);
}

// ===========================
// Modal (DOM-only, no innerHTML)
// ===========================

function openModal(title, buildContentFn) {
  document.getElementById('modalTitle').textContent = title;
  var body = document.getElementById('modalBody');
  body.textContent = '';
  buildContentFn(body);
  document.getElementById('modalOverlay').classList.add('active');
}

function closeModal(e) {
  if (!e || e.target === document.getElementById('modalOverlay')) {
    document.getElementById('modalOverlay').classList.remove('active');
  }
}

// ===========================
// Dashboard
// ===========================

var msgIn = 0, msgOut = 0, blocked = 0, tokensIn = 0, tokensOut = 0;

function loadDashboard() {
  fetchStatus();
}

function fetchStatus() {
  api.get('status').then(function(data) {
    var dot = document.getElementById('healthDot');
    dot.className = 'status-dot ' +
      (data.ready ? 'dot-green' : data.healthy ? 'dot-yellow' : 'dot-red');
    document.getElementById('healthText').textContent =
      data.ready ? 'Ready' : data.healthy ? 'Healthy' : 'Unhealthy';
    document.getElementById('uptime').textContent =
      Math.round(data.uptime_seconds) + 's';
    document.getElementById('llmStatus').textContent =
      data.llm_available ? 'Connected' : 'Disconnected';

    var pDiv = document.getElementById('dashPlatforms');
    pDiv.textContent = '';
    var platforms = data.platforms || {};
    for (var name in platforms) {
      var row = document.createElement('div');
      row.className = 'stat';
      var d = document.createElement('span');
      d.className = 'status-dot ' + (platforms[name] ? 'dot-green' : 'dot-red');
      row.appendChild(d);
      row.appendChild(document.createTextNode(name));
      pDiv.appendChild(row);
    }
  }).catch(function() { /* retry on next interval */ });
}

// Poll status
fetchStatus();
setInterval(fetchStatus, 5000);

// ===========================
// SSE Connection
// ===========================

function connectSSE() {
  var es = new EventSource('/dashboard/api/events?token=' + API_TOKEN);
  var el = document.getElementById('connStatus');

  es.onopen = function() {
    el.className = 'connection-status connected';
    el.textContent = 'Live';
  };
  es.onerror = function() {
    el.className = 'connection-status disconnected';
    el.textContent = 'Reconnecting...';
  };

  es.addEventListener('message_in', function(e) {
    msgIn++;
    document.getElementById('msgIn').textContent = msgIn;
    addEvent('message_in', JSON.parse(e.data));
  });
  es.addEventListener('message_out', function(e) {
    msgOut++;
    document.getElementById('msgOut').textContent = msgOut;
    var d = JSON.parse(e.data);
    tokensIn += (d.data && d.data.tokens_in) || 0;
    tokensOut += (d.data && d.data.tokens_out) || 0;
    document.getElementById('tokensIn').textContent = tokensIn.toLocaleString();
    document.getElementById('tokensOut').textContent = tokensOut.toLocaleString();
    addEvent('message_out', d);
  });
  es.addEventListener('auth_denied', function(e) {
    blocked++;
    document.getElementById('blocked').textContent = blocked;
    addEvent('auth_denied', JSON.parse(e.data));
  });
  es.addEventListener('rate_limited', function(e) {
    blocked++;
    document.getElementById('blocked').textContent = blocked;
    addEvent('rate_limited', JSON.parse(e.data));
  });
  es.addEventListener('error', function(e) {
    if (e.data) addEvent('error', JSON.parse(e.data));
  });
}

function addEvent(type, payload) {
  var evDiv = document.getElementById('events');
  var el = document.createElement('div');
  el.className = 'event type-' + type;

  var timeSpan = document.createElement('span');
  timeSpan.className = 'event-time';
  timeSpan.textContent = new Date().toLocaleTimeString();

  var typeSpan = document.createElement('span');
  typeSpan.className = 'event-type';
  typeSpan.textContent = type;

  var dataSpan = document.createElement('span');
  dataSpan.className = 'event-data';
  dataSpan.textContent = JSON.stringify(payload.data || payload).substring(0, 120);

  el.appendChild(timeSpan);
  el.appendChild(typeSpan);
  el.appendChild(dataSpan);
  evDiv.insertBefore(el, evDiv.firstChild);
  if (evDiv.children.length > 100) evDiv.removeChild(evDiv.lastChild);
}

connectSSE();

// ===========================
// Configuration
// ===========================

function loadConfig() {
  api.get('config').then(function(data) {
    document.getElementById('cfgSystemPrompt').value = data.system_prompt || '';
    document.getElementById('cfgMaxHistory').value = data.max_history || 20;
    document.getElementById('cfgLogLevel').value = data.log_level || 'INFO';
    document.getElementById('cfgLogJson').checked = !!data.log_json;

    var rl = data.rate_limit || {};
    document.getElementById('cfgRlUserCap').value = rl.user_capacity || 10;
    document.getElementById('cfgRlUserRate').value = rl.user_refill_rate || 1;
    document.getElementById('cfgRlGlobalCap').value = rl.global_capacity || 50;
    document.getElementById('cfgRlGlobalRate').value = rl.global_refill_rate || 10;
  });
}

function saveConfig(e) {
  e.preventDefault();
  var configBody = {
    system_prompt: document.getElementById('cfgSystemPrompt').value,
    max_history: parseInt(document.getElementById('cfgMaxHistory').value),
    log_level: document.getElementById('cfgLogLevel').value,
    log_json: document.getElementById('cfgLogJson').checked,
  };

  var rlBody = {
    user_capacity: parseFloat(document.getElementById('cfgRlUserCap').value),
    user_refill_rate: parseFloat(document.getElementById('cfgRlUserRate').value),
    global_capacity: parseFloat(document.getElementById('cfgRlGlobalCap').value),
    global_refill_rate: parseFloat(document.getElementById('cfgRlGlobalRate').value),
  };

  Promise.all([
    api.put('config', configBody),
    api.put('ratelimit', rlBody),
  ]).then(function(results) {
    var r1 = results[0], r2 = results[1];
    if (r1.ok && r2.ok) {
      toast('Configuration saved', 'success');
      if (r1.requires_restart) {
        toast('Some changes require restart', 'info');
      }
    } else {
      toast('Error saving config', 'error');
    }
  });
}

// ===========================
// Platforms
// ===========================

function loadPlatforms() {
  api.get('platforms').then(function(data) {
    var container = document.getElementById('platformsList');
    container.textContent = '';

    var platforms = data.platforms || {};
    for (var name in platforms) {
      var info = platforms[name];
      var card = document.createElement('div');
      card.className = 'platform-card';

      var nameEl = document.createElement('span');
      nameEl.className = 'platform-name';
      nameEl.textContent = name;

      var statusEl = document.createElement('div');
      statusEl.className = 'platform-status';

      var connDot = document.createElement('span');
      connDot.className = 'status-dot ' + (info.connected ? 'dot-green' : 'dot-red');
      var connText = document.createElement('span');
      connText.className = 'stat-label';
      connText.textContent = info.connected ? 'connected' : 'disconnected';

      var toggleLabel = document.createElement('label');
      toggleLabel.className = 'toggle';
      var toggleInput = document.createElement('input');
      toggleInput.type = 'checkbox';
      toggleInput.checked = info.enabled;
      toggleInput.dataset.platform = name;
      toggleInput.onchange = function() { togglePlatform(this.dataset.platform, this.checked); };
      var toggleSlider = document.createElement('span');
      toggleSlider.className = 'toggle-slider';
      toggleLabel.appendChild(toggleInput);
      toggleLabel.appendChild(toggleSlider);

      statusEl.appendChild(connDot);
      statusEl.appendChild(connText);
      statusEl.appendChild(toggleLabel);

      card.appendChild(nameEl);
      card.appendChild(statusEl);
      container.appendChild(card);
    }
  });
}

function togglePlatform(name, enabled) {
  api.put('platforms/' + name, { enabled: enabled }).then(function(data) {
    if (data.ok) {
      toast(name + (enabled ? ' enabled' : ' disabled') + ' (restart required)', 'info');
    } else {
      toast('Error: ' + (data.error || 'unknown'), 'error');
    }
  });
}

// ===========================
// LLM
// ===========================

function loadLLM() {
  api.get('llm').then(function(data) {
    document.getElementById('llmProvider').value = data.provider || 'claude';
    document.getElementById('llmModel').value = data.model || '';
    document.getElementById('llmTemp').value = data.temperature || 0.7;
    document.getElementById('tempValue').textContent = data.temperature || 0.7;
    document.getElementById('llmMaxTokens').value = data.max_tokens || 4096;
  });
}

function saveLLM(e) {
  e.preventDefault();
  var body = {
    provider: document.getElementById('llmProvider').value,
    model: document.getElementById('llmModel').value,
    temperature: parseFloat(document.getElementById('llmTemp').value),
    max_tokens: parseInt(document.getElementById('llmMaxTokens').value),
  };
  api.put('llm', body).then(function(data) {
    if (data.ok) {
      toast('LLM settings saved', 'success');
      if (data.requires_restart) {
        toast('Provider/model change requires restart', 'info');
      }
    } else {
      toast('Error saving LLM settings', 'error');
    }
  });
}

// ===========================
// Allowlist
// ===========================

function loadAllowlist() {
  api.get('allowlist').then(function(data) {
    var container = document.getElementById('allowlistTable');
    container.textContent = '';

    var users = data.users || [];
    if (users.length === 0) {
      var empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = 'No users in allowlist';
      container.appendChild(empty);
      return;
    }

    var table = document.createElement('table');
    table.className = 'table';
    var thead = document.createElement('thead');
    var headerRow = document.createElement('tr');
    ['Platform', 'User ID', 'Role', ''].forEach(function(text) {
      var th = document.createElement('th');
      th.textContent = text;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = document.createElement('tbody');
    users.forEach(function(user) {
      var tr = document.createElement('tr');

      var tdPlatform = document.createElement('td');
      tdPlatform.textContent = user.platform;
      var tdUser = document.createElement('td');
      tdUser.textContent = user.user_id;
      var tdRole = document.createElement('td');
      tdRole.textContent = user.role;

      var tdAction = document.createElement('td');
      var btn = document.createElement('button');
      btn.className = 'btn-sm btn-danger';
      btn.textContent = 'Remove';
      btn.onclick = (function(p, u) {
        return function() { removeAllowlistEntry(p, u); };
      })(user.platform, user.user_id);
      tdAction.appendChild(btn);

      tr.appendChild(tdPlatform);
      tr.appendChild(tdUser);
      tr.appendChild(tdRole);
      tr.appendChild(tdAction);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    container.appendChild(table);
  });
}

function addAllowlistEntry(e) {
  e.preventDefault();
  var body = {
    platform: document.getElementById('alPlatform').value,
    user_id: document.getElementById('alUserId').value,
    role: document.getElementById('alRole').value,
  };
  api.post('allowlist', body).then(function(data) {
    if (data.ok) {
      toast('User added to allowlist', 'success');
      document.getElementById('alUserId').value = '';
      loadAllowlist();
    } else {
      toast('Error: ' + (data.error || 'unknown'), 'error');
    }
  });
}

function removeAllowlistEntry(platform, userId) {
  api.del('allowlist', { platform: platform, user_id: userId }).then(function(data) {
    if (data.ok) {
      toast('User removed', 'success');
      loadAllowlist();
    } else {
      toast('Error: ' + (data.error || 'unknown'), 'error');
    }
  });
}

// ===========================
// Plugins
// ===========================

function loadPlugins() {
  api.get('plugins').then(function(data) {
    var container = document.getElementById('pluginsList');
    container.textContent = '';

    var plugins = data.plugins || [];
    if (plugins.length === 0) {
      var empty = document.createElement('div');
      empty.className = 'empty-state';
      var icon = document.createElement('div');
      icon.className = 'empty-icon';
      icon.textContent = '+';
      var text = document.createElement('div');
      text.textContent = 'No plugins installed. Use CLI: vaultbot plugin install <dir>';
      empty.appendChild(icon);
      empty.appendChild(text);
      container.appendChild(empty);
      return;
    }

    plugins.forEach(function(plugin) {
      var card = document.createElement('div');
      card.className = 'plugin-card';

      var header = document.createElement('div');
      header.className = 'plugin-header';

      var nameSpan = document.createElement('span');
      nameSpan.className = 'plugin-name';
      nameSpan.textContent = plugin.name;

      var verSpan = document.createElement('span');
      verSpan.className = 'plugin-version';
      verSpan.textContent = 'v' + plugin.version;
      if (plugin.author) verSpan.textContent += ' by ' + plugin.author;

      header.appendChild(nameSpan);
      header.appendChild(verSpan);

      var desc = document.createElement('div');
      desc.className = 'plugin-desc';
      desc.textContent = plugin.description || 'No description';

      var actions = document.createElement('div');
      actions.className = 'plugin-actions';

      var toggleLabel = document.createElement('label');
      toggleLabel.className = 'toggle';
      var toggleInput = document.createElement('input');
      toggleInput.type = 'checkbox';
      toggleInput.checked = plugin.enabled;
      toggleInput.dataset.name = plugin.name;
      toggleInput.onchange = function() { togglePlugin(this.dataset.name, this.checked); };
      var toggleSlider = document.createElement('span');
      toggleSlider.className = 'toggle-slider';
      toggleLabel.appendChild(toggleInput);
      toggleLabel.appendChild(toggleSlider);

      var statusText = document.createElement('span');
      statusText.className = 'stat-label';
      statusText.textContent = plugin.enabled ? 'enabled' : 'disabled';

      var uninstallBtn = document.createElement('button');
      uninstallBtn.className = 'btn-sm btn-danger';
      uninstallBtn.textContent = 'Uninstall';
      uninstallBtn.dataset.name = plugin.name;
      uninstallBtn.onclick = function() { uninstallPlugin(this.dataset.name); };

      actions.appendChild(toggleLabel);
      actions.appendChild(statusText);
      actions.appendChild(uninstallBtn);

      card.appendChild(header);
      card.appendChild(desc);
      card.appendChild(actions);
      container.appendChild(card);
    });
  });
}

function togglePlugin(name, enabled) {
  var action = enabled ? 'enable' : 'disable';
  api.post('plugins/' + encodeURIComponent(name) + '/' + action).then(function(data) {
    if (data.ok) {
      toast('Plugin ' + action + 'd: ' + name, 'success');
      loadPlugins();
    } else {
      toast('Error: ' + (data.error || 'unknown'), 'error');
      loadPlugins();
    }
  });
}

function uninstallPlugin(name) {
  if (!confirm('Uninstall plugin "' + name + '"?')) return;
  api.post('plugins/' + encodeURIComponent(name) + '/uninstall').then(function(data) {
    if (data.ok) {
      toast('Plugin uninstalled: ' + name, 'success');
      loadPlugins();
    } else {
      toast('Error: ' + (data.error || 'unknown'), 'error');
    }
  });
}

// ===========================
// Teams
// ===========================

function loadTeams() {
  api.get('teams').then(function(data) {
    var container = document.getElementById('teamsList');
    container.textContent = '';

    var teams = data.teams || [];
    if (teams.length === 0) {
      var empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = 'No teams created yet';
      container.appendChild(empty);
      return;
    }

    teams.forEach(function(team) {
      var card = document.createElement('div');
      card.className = 'card';

      var header = document.createElement('div');
      header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:12px';

      var titleEl = document.createElement('h3');
      titleEl.style.marginBottom = '0';
      titleEl.textContent = team.name;
      if (team.description) {
        var descSpan = document.createElement('span');
        descSpan.style.cssText = 'color:#666;font-size:0.85em;margin-left:8px;text-transform:none;letter-spacing:0';
        descSpan.textContent = '- ' + team.description;
        titleEl.appendChild(descSpan);
      }

      var deleteBtn = document.createElement('button');
      deleteBtn.className = 'btn-sm btn-danger';
      deleteBtn.textContent = 'Delete';
      deleteBtn.dataset.name = team.name;
      deleteBtn.onclick = function() { deleteTeam(this.dataset.name); };

      header.appendChild(titleEl);
      header.appendChild(deleteBtn);
      card.appendChild(header);

      // Members table
      var members = team.members || [];
      if (members.length > 0) {
        var table = document.createElement('table');
        table.className = 'table';
        table.style.marginBottom = '12px';
        var tbody = document.createElement('tbody');
        members.forEach(function(m) {
          var tr = document.createElement('tr');
          var td1 = document.createElement('td');
          td1.textContent = m.platform;
          var td2 = document.createElement('td');
          td2.textContent = m.user_id;
          var td3 = document.createElement('td');
          td3.textContent = m.role;
          var td4 = document.createElement('td');
          var rmBtn = document.createElement('button');
          rmBtn.className = 'btn-sm btn-danger';
          rmBtn.textContent = 'x';
          rmBtn.onclick = (function(tn, p, u) {
            return function() { removeTeamMember(tn, p, u); };
          })(team.name, m.platform, m.user_id);
          td4.appendChild(rmBtn);
          tr.appendChild(td1);
          tr.appendChild(td2);
          tr.appendChild(td3);
          tr.appendChild(td4);
          tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        card.appendChild(table);
      } else {
        var noMembers = document.createElement('div');
        noMembers.style.cssText = 'color:#555;margin-bottom:12px';
        noMembers.textContent = 'No members';
        card.appendChild(noMembers);
      }

      // Add member form
      var form = document.createElement('form');
      form.className = 'inline-form';
      form.dataset.team = team.name;
      form.onsubmit = function(e) {
        e.preventDefault();
        var teamN = this.dataset.team;
        var inputs = this.querySelectorAll('input, select');
        addTeamMember(teamN, inputs[0].value, inputs[1].value, inputs[2].value);
      };

      var platformOptions = ['telegram', 'discord', 'slack', 'whatsapp', 'signal', 'teams', 'imessage'];

      var fg1 = document.createElement('div');
      fg1.className = 'form-group';
      var sel = document.createElement('select');
      platformOptions.forEach(function(p) {
        var opt = document.createElement('option');
        opt.value = p;
        opt.textContent = p;
        sel.appendChild(opt);
      });
      fg1.appendChild(sel);

      var fg2 = document.createElement('div');
      fg2.className = 'form-group';
      var inp = document.createElement('input');
      inp.type = 'text';
      inp.placeholder = 'user_id';
      inp.required = true;
      fg2.appendChild(inp);

      var fg3 = document.createElement('div');
      fg3.className = 'form-group';
      var roleSel = document.createElement('select');
      ['user', 'admin'].forEach(function(r) {
        var opt = document.createElement('option');
        opt.value = r;
        opt.textContent = r;
        roleSel.appendChild(opt);
      });
      fg3.appendChild(roleSel);

      var addBtn = document.createElement('button');
      addBtn.type = 'submit';
      addBtn.className = 'btn-sm button-success';
      addBtn.textContent = 'Add';

      form.appendChild(fg1);
      form.appendChild(fg2);
      form.appendChild(fg3);
      form.appendChild(addBtn);
      card.appendChild(form);

      container.appendChild(card);
    });
  });
}

function createTeam(e) {
  e.preventDefault();
  var body = {
    name: document.getElementById('teamName').value,
    description: document.getElementById('teamDesc').value,
  };
  api.post('teams', body).then(function(data) {
    if (data.ok) {
      toast('Team created: ' + body.name, 'success');
      document.getElementById('teamName').value = '';
      document.getElementById('teamDesc').value = '';
      loadTeams();
    } else {
      toast('Error: ' + (data.error || 'unknown'), 'error');
    }
  });
}

function deleteTeam(name) {
  if (!confirm('Delete team "' + name + '"?')) return;
  api.del('teams/' + encodeURIComponent(name)).then(function(data) {
    if (data.ok) {
      toast('Team deleted', 'success');
      loadTeams();
    } else {
      toast('Error: ' + (data.error || 'unknown'), 'error');
    }
  });
}

function addTeamMember(teamName, platform, userId, role) {
  api.post('teams/' + encodeURIComponent(teamName) + '/members', {
    platform: platform,
    user_id: userId,
    role: role,
  }).then(function(data) {
    if (data.ok) {
      toast('Member added', 'success');
      loadTeams();
    } else {
      toast('Error: ' + (data.error || 'unknown'), 'error');
    }
  });
}

function removeTeamMember(teamName, platform, userId) {
  api.del('teams/' + encodeURIComponent(teamName) + '/members', {
    platform: platform,
    user_id: userId,
  }).then(function(data) {
    if (data.ok) {
      toast('Member removed', 'success');
      loadTeams();
    } else {
      toast('Error: ' + (data.error || 'unknown'), 'error');
    }
  });
}

// ===========================
// Credentials
// ===========================

function loadCredentials() {
  api.get('credentials').then(function(data) {
    var container = document.getElementById('credentialsList');
    container.textContent = '';

    var creds = data.credentials || [];
    creds.forEach(function(cred) {
      var row = document.createElement('div');
      row.className = 'cred-row';

      var keyEl = document.createElement('span');
      keyEl.className = 'cred-key';

      var dot = document.createElement('span');
      dot.className = 'status-dot ' + (cred.exists ? 'dot-green' : 'dot-red');

      keyEl.appendChild(dot);
      keyEl.appendChild(document.createTextNode(cred.key));

      var actions = document.createElement('div');
      actions.className = 'cred-actions';

      var setBtn = document.createElement('button');
      setBtn.className = 'btn-sm button-info';
      setBtn.textContent = cred.exists ? 'Update' : 'Set';
      setBtn.dataset.key = cred.key;
      setBtn.onclick = function() { showSetCredentialModal(this.dataset.key); };

      var delBtn = document.createElement('button');
      delBtn.className = 'btn-sm btn-danger';
      delBtn.textContent = 'Delete';
      delBtn.dataset.key = cred.key;
      delBtn.onclick = function() { deleteCredential(this.dataset.key); };
      if (!cred.exists) delBtn.disabled = true;

      actions.appendChild(setBtn);
      actions.appendChild(delBtn);

      row.appendChild(keyEl);
      row.appendChild(actions);
      container.appendChild(row);
    });
  });
}

function showSetCredentialModal(key) {
  openModal('Set Credential: ' + key, function(body) {
    var form = document.createElement('form');
    form.onsubmit = function(e) {
      e.preventDefault();
      var value = passInput.value;
      api.post('credentials/' + encodeURIComponent(key), { value: value }).then(function(data) {
        if (data.ok) {
          toast('Credential saved: ' + key, 'success');
          closeModal();
          loadCredentials();
        } else {
          toast('Error: ' + (data.error || 'unknown'), 'error');
        }
      });
    };

    var fg = document.createElement('div');
    fg.className = 'form-group';
    var label = document.createElement('label');
    label.textContent = 'Value';
    var passInput = document.createElement('input');
    passInput.type = 'password';
    passInput.required = true;
    passInput.placeholder = 'Enter credential value';
    fg.appendChild(label);
    fg.appendChild(passInput);

    var saveBtn = document.createElement('button');
    saveBtn.type = 'submit';
    saveBtn.className = 'button-success';
    saveBtn.textContent = 'Save';

    var cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'btn-sm';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.style.marginLeft = '8px';
    cancelBtn.onclick = function() { closeModal(); };

    form.appendChild(fg);
    form.appendChild(saveBtn);
    form.appendChild(cancelBtn);
    body.appendChild(form);

    // Auto-focus the input
    setTimeout(function() { passInput.focus(); }, 100);
  });
}

function deleteCredential(key) {
  if (!confirm('Delete credential "' + key + '"?')) return;
  api.del('credentials/' + encodeURIComponent(key)).then(function(data) {
    if (data.ok) {
      toast('Credential deleted', 'success');
      loadCredentials();
    } else {
      toast('Error: ' + (data.error || 'unknown'), 'error');
    }
  });
}

// ===========================
// Audit Log
// ===========================

function loadAudit() {
  var typeFilter = document.getElementById('auditTypeFilter').value;
  var path = 'audit?limit=100';
  if (typeFilter) path += '&type=' + encodeURIComponent(typeFilter);

  api.get(path).then(function(data) {
    var container = document.getElementById('auditTable');
    container.textContent = '';

    var events = data.events || [];
    if (events.length === 0) {
      var empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = 'No audit events recorded yet';
      container.appendChild(empty);
      return;
    }

    var table = document.createElement('table');
    table.className = 'table audit-table';
    var thead = document.createElement('thead');
    var headerRow = document.createElement('tr');
    ['Time', 'Type', 'Platform', 'User', 'Details'].forEach(function(text) {
      var th = document.createElement('th');
      th.textContent = text;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = document.createElement('tbody');
    events.forEach(function(evt) {
      var tr = document.createElement('tr');

      var tdTime = document.createElement('td');
      tdTime.style.color = '#555';
      tdTime.textContent = new Date(evt.timestamp * 1000).toLocaleString();

      var tdType = document.createElement('td');
      tdType.textContent = evt.type;
      if (evt.type.indexOf('denied') >= 0 || evt.type === 'error') {
        tdType.style.color = '#ff3d3d';
      } else if (evt.type.indexOf('success') >= 0) {
        tdType.style.color = '#00ff7a';
      } else if (evt.type === 'config.changed') {
        tdType.style.color = '#ffce65';
      } else {
        tdType.style.color = '#67daff';
      }

      var tdPlatform = document.createElement('td');
      tdPlatform.textContent = evt.platform || '-';

      var tdUser = document.createElement('td');
      tdUser.textContent = evt.user_id || '-';

      var tdDetails = document.createElement('td');
      tdDetails.style.color = '#888';
      tdDetails.textContent = JSON.stringify(evt.details || {}).substring(0, 80);

      tr.appendChild(tdTime);
      tr.appendChild(tdType);
      tr.appendChild(tdPlatform);
      tr.appendChild(tdUser);
      tr.appendChild(tdDetails);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    container.appendChild(table);
  });
}
