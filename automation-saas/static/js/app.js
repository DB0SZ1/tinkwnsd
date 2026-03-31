(function(){
  // Global Toast System
  window.showToast = function(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<div class="toast-content">${type === 'success' ? '✔️' : '❌'} ${message}</div>`;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  };

  // SIDEBAR
  var sidebar = document.getElementById('sidebar');
  var backdrop = document.getElementById('backdrop');
  var hamburger = document.getElementById('hamburger');
  if(hamburger) {
      hamburger.addEventListener('click', function(){
        sidebar.classList.add('open');
        backdrop.classList.add('open');
      });
  }
  if(backdrop) {
      backdrop.addEventListener('click', function(){
        sidebar.classList.remove('open');
        backdrop.classList.remove('open');
      });
  }

  // NAV
  document.querySelectorAll('[data-nav]').forEach(function(el){
    el.addEventListener('click', function(e){
      e.preventDefault();
      document.querySelectorAll('[data-nav]').forEach(function(n){ n.classList.remove('active'); });
      el.classList.add('active');
      
      var target = el.getAttribute('data-nav');
      document.querySelectorAll('.tab-content').forEach(function(tc){ tc.style.display = 'none'; });
      var targetEl = document.getElementById('tab-' + target);
      if(targetEl) {
        targetEl.style.display = 'block';
        if(target === 'persona') fetchPersona();
        if(target === 'health') {
            fetchHealth();
            startLogPolling();
        } else {
            stopLogPolling();
        }
      }

      if(window.innerWidth <= 768){
        sidebar.classList.remove('open');
        backdrop.classList.remove('open');
      }
    });
  });

  // MODALS
  function openModal(id){ 
      var o=document.getElementById(id); 
      if(!o) return; 
      o.style.display='flex'; 
      if(id === 'modal-settings') fetchSettings();
      requestAnimationFrame(function(){ 
          requestAnimationFrame(function(){ 
              o.classList.add('open'); 
          }); 
      }); 
  }

  async function fetchSettings() {
    try {
        let res = await fetch('/api/v1/settings');
        if(!res.ok) return;
        let d = await res.json();
        
        // Map backend keys to modal input IDs
        const map = {
            "OPENROUTER_API_KEY": "set-or-key",
            "OPENROUTER_MODEL": "set-or-model",
            "X_API_KEY": "set-x-key",
            "X_API_SECRET": "set-x-secret",
            "X_ACCESS_TOKEN": "set-x-token",
            "X_ACCESS_TOKEN_SECRET": "set-x-token-secret",
            "X_USERNAME": "set-x-user",
            "X_EMAIL": "set-x-email",
            "X_PASSWORD": "set-x-pass",
            "LINKEDIN_ACCESS_TOKEN": "set-li-token",
            "LINKEDIN_PERSON_ID": "set-li-urn",
            "TOPICS_ENGINE": "set-topic-engine",
            "WOEID": "set-woeid",
            "DATABASE_URL": "set-db",
            "ADMIN_API_KEY": "set-admin-key",
            "TIMEZONE": "set-tz",
            "X_SCHEDULE_HOURS": "set-x-schedule",
            "LI_SCHEDULE_HOURS": "set-li-schedule"
        };
        
        for(let key in map) {
            let el = document.getElementById(map[key]);
            if(el) el.value = d[key] || "";
        }
    } catch(e) {}
  }
  
  function closeModal(id){ 
      var o=document.getElementById(id); 
      if(!o) return; 
      o.classList.remove('open'); 
      setTimeout(function(){ 
          o.style.display='none'; 
      },300); 
  }
  
  // DELETE TOPIC (OLD confirm replaced by Modal)
  window.deleteTopic = function(id) {
    var modal = document.getElementById('modal-delete-confirm');
    var hdnId = document.getElementById('hdn-delete-id');
    if(!modal || !hdnId) return;
    
    hdnId.value = id;
    openModal('modal-delete-confirm');
  };

  // CONFIRM DELETE ACTION
  var btnConfirmDelete = document.getElementById('btn-confirm-delete');
  if(btnConfirmDelete) {
    btnConfirmDelete.addEventListener('click', async function() {
        var id = document.getElementById('hdn-delete-id').value;
        var originalHtml = this.innerHTML;
        this.innerHTML = '<span class="loading-spin">🔄</span> Deleting...';
        this.disabled = true;

        try {
            let res = await fetch(`/api/v1/topics/${id}`, { method: 'DELETE' });
            if(res.ok) {
                showToast('Topic permanently removed.');
                closeModal('modal-delete-confirm');
                var el = document.querySelector(`[data-topic-id="${id}"]`);
                if(el) el.remove();
                // If it's a trend, refresh the trends count badge
                setTimeout(() => location.reload(), 500); 
            } else {
                showToast('Delete failed.', 'error');
            }
        } catch(e) {
            showToast('Network error.', 'error');
        } finally {
            this.innerHTML = originalHtml;
            this.disabled = false;
        }
    });
  }

  // Delegated Delete Listener for data attributes
  document.addEventListener('click', function(e) {
      var btn = e.target.closest('[data-delete-topic-id]');
      if(btn) {
          deleteTopic(btn.getAttribute('data-delete-topic-id'));
      }
  });

  // MANUAL ENGINE SCOUT
  var btnScout = document.getElementById('btn-scout-trends');
  if(btnScout) {
      btnScout.addEventListener('click', async function(){
          var originalHtml = this.innerHTML;
          this.innerHTML = '<span class="loading-spin">🔄</span> Scouting...';
          this.disabled = true;

          try {
              let res = await fetch('/api/v1/engine/scout', { method: 'POST' });
              let data = await res.json();
              if(data.status === 'success') {
                  showToast('Scouting successful! Found ' + (data.new_topics ? data.new_topics.length : 0) + ' trends.');
                  console.log("Trend Context Preview:", data.context_preview);
                  setTimeout(() => location.reload(), 2000);
              } else {
                  showToast('Scouting failed: ' + data.message, 'error');
              }
          } catch(e) {
              showToast('Network error.', 'error');
          } finally {
              this.innerHTML = originalHtml;
              this.disabled = false;
          }
      });
  }

  document.querySelectorAll('[data-open]').forEach(function(el){ 
      el.addEventListener('click', function(){ openModal(el.getAttribute('data-open')); }); 
  });
  document.querySelectorAll('[data-close]').forEach(function(el){ 
      el.addEventListener('click', function(e){ 
          e.stopPropagation();
          closeModal(el.getAttribute('data-close')); 
      }); 
  });
  document.querySelectorAll('.modal-overlay').forEach(function(o){ 
      o.addEventListener('click', function(e){ if(e.target===o) closeModal(o.id); }); 
  });
  document.addEventListener('keydown', function(e){ 
      if(e.key==='Escape') {
          document.querySelectorAll('.modal-overlay.open').forEach(function(o){ closeModal(o.id); }); 
      }
  });

  // PLATFORM TOGGLES (Distribute To tags)
  // Dashboard
  var togLi = document.getElementById('tog-li');
  var togXt = document.getElementById('tog-xt');
  if(togLi) togLi.addEventListener('click', function(){ this.classList.toggle('on'); });
  if(togXt) togXt.addEventListener('click', function(){ this.classList.toggle('on'); });
  
  // Modal
  var mtogLi = document.getElementById('modal-tog-li');
  var mtogXt = document.getElementById('modal-tog-xt');
  if(mtogLi) mtogLi.addEventListener('click', function(){ this.classList.toggle('on'); });
  if(mtogXt) mtogXt.addEventListener('click', function(){ this.classList.toggle('on'); });

  // PLATFORM PUBLISHING ON/OFF BUTTONS
  document.querySelectorAll('.platform-card').forEach(function(card){
    var dot = card.querySelector('.plat-mode-dot');
    var txt = card.querySelector('.plat-mode');
    
    if(txt) {
      txt.style.cursor = 'pointer';
      txt.addEventListener('click', async function(){
        var isLi = card.classList.contains('linkedin');
        var plat = isLi ? 'linkedin' : 'x';
        var originalHtml = txt.innerHTML;
        
        txt.innerHTML = 'Updating...';
        
        try {
          let res = await fetch(`/api/v1/jobs/${plat}/toggle`, { method: 'POST' });
          let data = await res.json();
          
          if(data.status === 'paused') {
            dot.classList.remove('on');
            txt.innerHTML = '<div class="plat-mode-dot"></div> Publishing Paused';
          } else if(data.status === 'resumed') {
            dot.classList.add('on');
            txt.innerHTML = '<div class="plat-mode-dot on"></div> Publishing Active';
          } else {
            txt.innerHTML = originalHtml;
          }
        } catch(e) {
          txt.innerHTML = originalHtml;
        }
      });
    }
  });

  // PERSONALITY
  document.querySelectorAll('[data-mode]').forEach(function(el){
    el.addEventListener('click', function(){
      document.querySelectorAll('[data-mode]').forEach(function(m){ m.classList.remove('active'); });
      el.classList.add('active');
      document.getElementById('hdn-personality').value = el.getAttribute('data-mode-value');
    });
  });

  // Topic Submission Logic
  async function submitTopicData(topic, platform, flavor, personality, btn) {
      if(!topic) {
          showToast('Please enter a topic!', 'error');
          return;
      }
      
      var originalText = btn.innerHTML;
      btn.innerHTML = 'Saving...';

      try {
          let res = await fetch('/api/v1/topics', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                  topic: topic,
                  platform: platform,
                  flavor: flavor,
                  personality: personality
              })
          });
          if(res.ok) {
              showToast('Topic added to the engine!');
              setTimeout(() => location.reload(), 800);
          } else {
              showToast('Failed to save topic.', 'error');
              setTimeout(() => btn.innerHTML = originalText, 2000);
          }
      } catch(e) {
          showToast('Network error.', 'error');
          setTimeout(() => btn.innerHTML = originalText, 2000);
      }
  }

  // Dashboard Submission
  var submitTopic = document.getElementById('btn-submit-topic');
  if(submitTopic) {
      submitTopic.addEventListener('click', function(){
          var topic = document.getElementById('topicInput').value;
          var flavor = document.getElementById('flavorSelect').value || "random";
          var personality = document.getElementById('hdn-personality').value;
          
          var isLi = document.getElementById('tog-li').classList.contains('on');
          var isXt = document.getElementById('tog-xt').classList.contains('on');
          
          var platform = "both";
          if (isLi && !isXt) platform = "linkedin";
          if (!isLi && isXt) platform = "x";
          if (!isLi && !isXt) {
              showToast('Select a platform!', 'error');
              return;
          }

          submitTopicData(topic, platform, flavor, personality, this);
      });
  }

  // Modal Submission
  var modalSubmitTopic = document.getElementById('btn-modal-submit-topic');
  if(modalSubmitTopic) {
      modalSubmitTopic.addEventListener('click', function(){
          var topic = document.getElementById('modalTopicInput').value;
          var flavor = document.getElementById('modalFlavorSelect').value || "random";
          var personality = document.getElementById('hdn-personality').value; // Share singleton
          
          var isLi = document.getElementById('modal-tog-li').classList.contains('on');
          var isXt = document.getElementById('modal-tog-xt').classList.contains('on');
          
          var platform = "both";
          if (isLi && !isXt) platform = "linkedin";
          if (!isLi && isXt) platform = "x";
          if (!isLi && !isXt) {
              showToast('Select a platform!', 'error');
              return;
          }

          submitTopicData(topic, platform, flavor, personality, this);
      });
  }

  // File Upload
  var upzone = document.getElementById('upload-zone');
  var fileInput = document.getElementById('file-input');
  var btnUpload = document.getElementById('btn-upload');

  if(upzone && fileInput) {
      upzone.addEventListener('click', () => fileInput.click());
      
      fileInput.addEventListener('change', function() {
          if(this.files && this.files.length > 0) {
              document.getElementById('upload-title').innerText = this.files[0].name;
          }
      });

      btnUpload.addEventListener('click', async function() {
          if(!fileInput.files || fileInput.files.length === 0) return;
          
          let tag = document.getElementById('img-tag-select').value;
          let desc = document.getElementById('img-desc').value;
          let cUrl = document.getElementById('img-cloudinary-url').value;
          
          let formData = new FormData();
          if(fileInput.files.length > 0) formData.append('file', fileInput.files[0]);
          formData.append('tag', tag);
          formData.append('description', desc);
          formData.append('cloudinary_url', cUrl);

          var originalText = this.innerHTML;
          this.innerHTML = 'Uploading...';

          try {
              let res = await fetch('/api/v1/images', {
                  method: 'POST',
                  body: formData
              });
              if(res.ok) {
                  showToast('Image uploaded and categorized!');
                  setTimeout(() => location.reload(), 800);
              } else {
                  showToast('Upload failed.', 'error');
                  setTimeout(() => this.innerHTML = originalText, 2000);
              }
          } catch(e) {
              this.innerHTML = 'Error';
              setTimeout(() => this.innerHTML = originalText, 2000);
          }
      });
  }

  // Settings Save
  var btnSettings = document.getElementById('btn-save-settings');
  if(btnSettings) {
      btnSettings.addEventListener('click', async function() {
          var orKey = document.getElementById('set-or-key').value;
          var xKey = document.getElementById('set-x-key').value;
          var liUrn = document.getElementById('set-li-urn').value;

          var originalText = this.innerHTML;
          this.innerHTML = 'Saving...';

          try {
              let res = await fetch('/api/v1/settings', {
                  method: 'POST',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({
                      openrouter_api_key: document.getElementById('set-or-key').value,
                      openrouter_model: document.getElementById('set-or-model').value,
                      
                      x_api_key: document.getElementById('set-x-key').value,
                      x_api_secret: document.getElementById('set-x-secret').value,
                      x_access_token: document.getElementById('set-x-token').value,
                      x_access_token_secret: document.getElementById('set-x-token-secret').value,
                      
                      x_username: document.getElementById('set-x-user').value,
                      x_email: document.getElementById('set-x-email').value,
                      x_password: document.getElementById('set-x-pass').value,
                      
                      linkedin_access_token: document.getElementById('set-li-token').value,
                      linkedin_urn: document.getElementById('set-li-urn').value,
                      
                      topics_engine: document.getElementById('set-topic-engine').value,
                      woeid: document.getElementById('set-woeid').value,
                      
                      database_url: document.getElementById('set-db').value,
                      admin_api_key: document.getElementById('set-admin-key').value,
                      timezone: document.getElementById('set-tz').value,
                      x_schedule_hours: document.getElementById('set-x-schedule').value,
                      li_schedule_hours: document.getElementById('set-li-schedule').value
                  })
              });
              if(res.ok) {
                  showToast('Settings updated successfully!');
                  setTimeout(() => closeModal('modal-settings'), 800);
                  setTimeout(() => this.innerHTML = originalText, 1000);
              } else {
                  showToast('Could not save settings.', 'error');
                  setTimeout(() => this.innerHTML = originalText, 2000);
              }
          } catch(e) {
              this.innerHTML = 'Error';
              setTimeout(() => this.innerHTML = originalText, 2000);
          }
      });
  }

  // System Health Logic
  let logInterval = null;

  async function fetchHealth() {
    console.log("Fetching system health...");
    try {
        let res = await fetch('/api/v1/system/health');
        let d = await res.json();
        console.log("Health data received:", d);
        
        document.getElementById('health-timestamp').innerText = `Last Checked: ${d.timestamp}`;

        updateHealthItem('health-db', d.database === "healthy" ? "healthy" : "ERROR");
        updateHealthItem('health-or', d.openrouter);
        updateHealthItem('health-x', d.x.status);
        updateHealthItem('health-li', d.linkedin.status);
    } catch(e) {
        console.error("Health fetch failed:", e);
    }
  }

  function updateHealthItem(id, status) {
    let el = document.getElementById(id);
    if(!el) return;
    let dot = el.querySelector('.h-dot');
    let pill = el.querySelector('.h-pill');
    
    // Status normalization
    let s = status.toLowerCase();
    let isHealthy = s === 'healthy';
    let isAuthError = s.includes('unauthorized') || s.includes('denied') || s.includes('401');

    if(isHealthy) {
        dot.className = 'h-dot on';
        pill.className = 'h-pill healthy';
        pill.innerText = 'Connected';
    } else if(isAuthError) {
        dot.className = 'h-dot off';
        pill.className = 'h-pill unauthorized';
        pill.innerText = 'Unauthorized';
    } else {
        dot.className = 'h-dot off';
        pill.className = 'h-pill error';
        pill.innerText = status.toUpperCase().substring(0, 15);
    }
  }

  async function fetchLogs() {
    console.log("Fetching system logs...");
    try {
        let res = await fetch('/api/v1/system/logs');
        let d = await res.json();
        let consoleDiv = document.getElementById('log-console');
        if(consoleDiv) {
            consoleDiv.innerText = d.logs || "No logs yet.";
            consoleDiv.scrollTop = consoleDiv.scrollHeight;
        }
    } catch(e) {
        console.error("Log fetch failed:", e);
    }
  }

  function startLogPolling() {
    fetchLogs();
    if(!logInterval) logInterval = setInterval(fetchLogs, 5000);
  }

  function stopLogPolling() {
    if(logInterval) {
        clearInterval(logInterval);
        logInterval = null;
    }
  }

  // Manual Triggers
  async function forcePost(platform, btn) {
    var originalText = btn.innerHTML;
    btn.innerHTML = '<span class="loading-spin">🔄</span> Processing...';
    btn.disabled = true;

    try {
        let res = await fetch(`/api/v1/system/manual-post/${platform}`, { method: 'POST' });
        let d = await res.json();
        if(d.status === 'success') {
            showToast(d.message);
        } else {
            showToast(d.message, 'error');
        }
    } catch(e) {
        showToast('Network error.', 'error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
        fetchLogs();
    }
  }

  var btnForceX = document.getElementById('btn-force-x');
  if(btnForceX) btnForceX.addEventListener('click', () => forcePost('x', btnForceX));
  
  var btnForceLi = document.getElementById('btn-force-li');
  if(btnForceLi) btnForceLi.addEventListener('click', () => forcePost('linkedin', btnForceLi));

  var btnRefreshLogs = document.getElementById('btn-refresh-logs');
  if(btnRefreshLogs) btnRefreshLogs.addEventListener('click', fetchLogs);

  // Persona Logic
  async function fetchPersona() {
    try {
        let res = await fetch('/api/v1/persona');
        let d = await res.json();
        document.getElementById('persona-content').value = d['persona.md'] || "";
        document.getElementById('how-to-write-content').value = d['how_to_write.md'] || "";
        document.getElementById('memory-content').value = d['memory.md'] || "";
    } catch(e) {
        showToast('Failed to load persona files.', 'error');
    }
  }

  var btnSavePersona = document.getElementById('btn-save-persona');
  if(btnSavePersona) {
    btnSavePersona.addEventListener('click', async function(){
        var originalText = this.innerHTML;
        this.innerHTML = 'Saving...';
        try {
            let res = await fetch('/api/v1/persona', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    'persona.md': document.getElementById('persona-content').value,
                    'how_to_write.md': document.getElementById('how-to-write-content').value,
                    'memory.md': document.getElementById('memory-content').value
                })
            });
            if(res.ok) {
                showToast('AI Persona Core updated!');
            } else {
                showToast('Failed to save persona.', 'error');
            }
        } catch(e) {
            showToast('Network error.', 'error');
        } finally {
            setTimeout(() => this.innerHTML = originalText, 1000);
        }
    });
  }

  // X Health Check
  var btnXDebug = document.getElementById('btn-x-debug');
  if(btnXDebug) {
    btnXDebug.addEventListener('click', async function(){
        var originalText = this.innerHTML;
        this.innerHTML = 'Checking...';
        try {
            let res = await fetch('/api/v1/debug/x-auth');
            let d = await res.json();
            if(d.status === 'success') {
                showToast('X Authentication Healthy!', 'success');
            } else {
                // Show the specific error if it failed
                alert("X Diagnostic Failure:\n\n" + d.error + "\n\nCheck terminal for full trace.");
                showToast('X Auth Failed.', 'error');
            }
        } catch(e) {
            showToast('Network error.', 'error');
        } finally {
            this.innerHTML = originalText;
        }
    });
  }

})();
