document.addEventListener('DOMContentLoaded', function () {
  // 1. Sidebar Elements
  const sidebar = document.getElementById('appSidebar');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');
  const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
  const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');

  // Check saved desktop collapse state
  if (window.innerWidth >= 992) {
    const isCollapsed = localStorage.getItem('sed_sidebar_collapsed') === 'true';
    if (isCollapsed) {
      document.body.classList.add('sidebar-collapsed');
      if (sidebarToggleBtn) {
        sidebarToggleBtn.classList.add('is-active');
      }
    }
  }

  // Toggle Function
  function toggleSidebar() {
    if (window.innerWidth < 992) {
      // Mobile / Tablet Drawer Mode
      if (sidebar) {
        const isOpen = sidebar.classList.toggle('show');
        if (sidebarBackdrop) {
          sidebarBackdrop.classList.toggle('show', isOpen);
        }
        if (sidebarToggleBtn) {
          sidebarToggleBtn.classList.toggle('is-active', isOpen);
        }
      }
    } else {
      // Desktop Collapsed Icon-Mode
      const isNowCollapsed = document.body.classList.toggle('sidebar-collapsed');
      localStorage.setItem('sed_sidebar_collapsed', isNowCollapsed ? 'true' : 'false');
      if (sidebarToggleBtn) {
        sidebarToggleBtn.classList.toggle('is-active', isNowCollapsed);
      }
    }
  }

  function closeMobileSidebar() {
    if (sidebar) {
      sidebar.classList.remove('show');
    }
    if (sidebarBackdrop) {
      sidebarBackdrop.classList.remove('show');
    }
    if (sidebarToggleBtn && window.innerWidth < 992) {
      sidebarToggleBtn.classList.remove('is-active');
    }
  }

  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      toggleSidebar();
    });
  }

  if (sidebarCloseBtn) {
    sidebarCloseBtn.addEventListener('click', function () {
      closeMobileSidebar();
    });
  }

  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', function () {
      closeMobileSidebar();
    });
  }

  // Close mobile sidebar when clicking any navigation link
  const navLinks = document.querySelectorAll('.side-menu-link');
  navLinks.forEach(function (link) {
    link.addEventListener('click', function () {
      if (window.innerWidth < 992) {
        closeMobileSidebar();
      }
    });
  });

  // Handle window resize gracefully
  window.addEventListener('resize', function () {
    if (window.innerWidth >= 992) {
      if (sidebarBackdrop) {
        sidebarBackdrop.classList.remove('show');
      }
      if (sidebar) {
        sidebar.classList.remove('show');
      }
      const isCollapsed = localStorage.getItem('sed_sidebar_collapsed') === 'true';
      if (sidebarToggleBtn) {
        sidebarToggleBtn.classList.toggle('is-active', isCollapsed);
      }
    } else {
      document.body.classList.remove('sidebar-collapsed');
      if (sidebarToggleBtn && (!sidebar || !sidebar.classList.contains('show'))) {
        sidebarToggleBtn.classList.remove('is-active');
      }
    }
  });

  // 2. Auto-dismiss alerts after 6 seconds
  setTimeout(function () {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    });
  }, 6000);

  // 3. Client-side instant filter for data tables
  const searchInput = document.getElementById('tableFilterInput');
  if (searchInput) {
    searchInput.addEventListener('keyup', function () {
      const filter = searchInput.value.toLowerCase();
      const rows = document.querySelectorAll('.filterable-table tbody tr');
      rows.forEach(function (row) {
        const text = row.innerText.toLowerCase();
        row.style.display = text.indexOf(filter) > -1 ? '' : 'none';
      });
    });
  }

  // 4. Automated Session Expiry & Inactivity Warning Manager
  const sessionConfigMeta = document.querySelector('meta[name="session-timeout-seconds"]');
  if (sessionConfigMeta) {
    const totalTimeoutSec = parseInt(sessionConfigMeta.getAttribute('content'), 10) || 600; // default 10 min (600s)
    const warningLeadSec = Math.min(120, Math.max(30, Math.floor(totalTimeoutSec / 4))); // 2 minutes warning
    let remainingSeconds = totalTimeoutSec;
    let timerInterval = null;
    let modalInstance = null;
    let warningShown = false;
    let lastKeepAliveSent = Date.now();

    const timeoutModalEl = document.getElementById('sessionTimeoutModal');
    const countdownDisplay = document.getElementById('sessionCountdownDisplay');
    const countdownSec = document.getElementById('sessionCountdownSeconds');
    const staySignedInBtn = document.getElementById('staySignedInBtn');

    if (timeoutModalEl && typeof bootstrap !== 'undefined') {
      modalInstance = new bootstrap.Modal(timeoutModalEl, {
        backdrop: 'static',
        keyboard: false
      });
    }

    function formatTime(seconds) {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }

    function pingKeepAlive(callback) {
      fetch('/auth/keep-alive', {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json'
        }
      })
      .then(function (response) {
        if (!response.ok) {
          window.location.href = '/auth/login?reason=timeout';
          return;
        }
        return response.json();
      })
      .then(function (data) {
        if (data && data.authenticated) {
          remainingSeconds = data.remaining_seconds || totalTimeoutSec;
          lastKeepAliveSent = Date.now();
          warningShown = false;
          if (modalInstance && timeoutModalEl.classList.contains('show')) {
            modalInstance.hide();
          }
          if (callback) callback(data);
        } else if (data && data.redirect) {
          window.location.href = data.redirect;
        }
      })
      .catch(function (err) {
        console.warn('Session keep-alive ping error:', err);
      });
    }

    // Reset client countdown on user interaction
    function onUserInteraction() {
      // If modal is actively visible, user must explicitly click "Stay Signed In"
      if (warningShown) return;

      remainingSeconds = totalTimeoutSec;

      // Periodically refresh server session if user is actively interacting (at most once every 3 minutes)
      const now = Date.now();
      if (now - lastKeepAliveSent > 180000) {
        lastKeepAliveSent = now;
        pingKeepAlive();
      }
    }

    // Listen to user interaction events with throttling
    ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'].forEach(function (evtName) {
      let throttled = false;
      window.addEventListener(evtName, function () {
        if (!throttled) {
          onUserInteraction();
          throttled = true;
          setTimeout(function () { throttled = false; }, 2000);
        }
      }, { passive: true });
    });

    if (staySignedInBtn) {
      staySignedInBtn.addEventListener('click', function () {
        staySignedInBtn.disabled = true;
        staySignedInBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Extending Session...';
        pingKeepAlive(function () {
          staySignedInBtn.disabled = false;
          staySignedInBtn.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i> Stay Signed In';
        });
      });
    }

    // Countdown tick every 1 second
    timerInterval = setInterval(function () {
      remainingSeconds--;

      if (remainingSeconds <= warningLeadSec && remainingSeconds > 0) {
        if (!warningShown && modalInstance) {
          warningShown = true;
          modalInstance.show();
        }
        if (countdownDisplay) {
          countdownDisplay.textContent = formatTime(remainingSeconds);
        }
        if (countdownSec) {
          countdownSec.textContent = remainingSeconds;
        }
      } else if (remainingSeconds <= 0) {
        clearInterval(timerInterval);
        if (modalInstance) {
          modalInstance.hide();
        }
        window.location.href = '/auth/logout?reason=timeout';
      }
    }, 1000);
  }
});
