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
      if(targetEl) targetEl.style.display = 'block';

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
            "TIMEZONE": "set-tz"
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
  
  window.deleteTopic = async function(id) {
    if(!confirm('Are you sure you want to delete this topic?')) return;
    try {
        let res = await fetch(`/api/v1/topics/${id}`, { method: 'DELETE' });
        if(res.ok) {
            showToast('Topic deleted.');
            var el = document.querySelector(`[data-topic-id="${id}"]`);
            if(el) el.remove();
        } else {
            showToast('Delete failed.', 'error');
        }
    } catch(e) {
        showToast('Network error.', 'error');
    }
  };

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
                  showToast('Scouting successful! Check logs for trends.');
                  console.log("Trend Context Preview:", data.context_preview);
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
                      timezone: document.getElementById('set-tz').value
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

})();
