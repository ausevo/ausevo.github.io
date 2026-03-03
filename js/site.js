/* AES Site.js — Australasian Evolution Society
   Vanilla JS only — no dependencies */

(function () {
  'use strict';

  // ─── Navbar ────────────────────────────────────────────────────────────────

  var nav     = document.querySelector('.site-nav');
  var toggle  = document.getElementById('nav-toggle');
  var menu    = document.getElementById('nav-menu');

  function closeMenu() {
    if (!menu) return;
    menu.classList.remove('is-open');
    if (toggle) {
      toggle.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    }
    document.body.style.overflow = '';
  }

  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      var open = menu.classList.toggle('is-open');
      toggle.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      document.body.style.overflow = open ? 'hidden' : '';
    });

    // Close when clicking outside
    document.addEventListener('click', function (e) {
      if (nav && !nav.contains(e.target) && menu.classList.contains('is-open')) {
        closeMenu();
      }
    });

    // Close on Escape
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeMenu();
    });
  }

  // Dropdown toggles (mobile + keyboard)
  document.querySelectorAll('.nav__link--parent').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      var item   = btn.closest('.nav__item--has-children');
      var isOpen = item.classList.toggle('is-open');
      btn.setAttribute('aria-expanded', String(isOpen));

      // Close sibling dropdowns
      document.querySelectorAll('.nav__item--has-children').forEach(function (sib) {
        if (sib !== item) {
          sib.classList.remove('is-open');
          var sibBtn = sib.querySelector('.nav__link--parent');
          if (sibBtn) sibBtn.setAttribute('aria-expanded', 'false');
        }
      });

      e.stopPropagation();
    });
  });

  // ─── Scroll: fill navbar on homepage ────────────────────────────────────────

  if (nav) {
    var isHome = document.body.classList.contains('layout-home');

    function onScroll() {
      nav.classList.toggle('is-scrolled', window.scrollY > 60);
    }

    if (isHome) {
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
    } else {
      // Non-homepage pages always have solid nav appearance
      nav.classList.add('is-scrolled');
    }
  }

  // ─── Hero image rotation ─────────────────────────────────────────────────────

  var slides = document.querySelectorAll('.hero__slide');
  if (slides.length > 1) {
    var current = 0;
    setInterval(function () {
      slides[current].classList.remove('is-active');
      current = (current + 1) % slides.length;
      slides[current].classList.add('is-active');
    }, 6000);
  }

  // ─── Countdown timer ─────────────────────────────────────────────────────────

  var countdownEl = document.getElementById('countdown');
  if (countdownEl) {
    // Parse the date; assume 9am local on conference start date
    var rawDate = countdownEl.dataset.target;
    var target  = rawDate ? new Date(rawDate + 'T09:00:00') : null;

    if (target && !isNaN(target)) {
      function updateCountdown() {
        var diff = target - Date.now();
        if (diff <= 0) {
          countdownEl.remove();
          return;
        }
        var days = Math.floor(diff / 86400000);
        var hrs  = Math.floor((diff % 86400000) / 3600000);
        var mins = Math.floor((diff % 3600000) / 60000);

        var dEl = countdownEl.querySelector('[data-unit="days"]');
        var hEl = countdownEl.querySelector('[data-unit="hrs"]');
        var mEl = countdownEl.querySelector('[data-unit="mins"]');

        if (dEl) dEl.textContent = days;
        if (hEl) hEl.textContent = String(hrs).padStart(2, '0');
        if (mEl) mEl.textContent = String(mins).padStart(2, '0');
      }

      updateCountdown();
      setInterval(updateCountdown, 60000);
    } else {
      countdownEl.remove();
    }
  }

  // ─── Analytics tracking ──────────────────────────────────────────────────────
  // Fires GA4 events for elements with data-track="event-name"
  // Optional: data-track-category="category"

  document.querySelectorAll('[data-track]').forEach(function (el) {
    el.addEventListener('click', function () {
      if (typeof gtag !== 'function') return;
      gtag('event', el.dataset.track, {
        event_category: el.dataset.trackCategory || 'engagement',
        event_label:    el.href || el.textContent.trim().slice(0, 80)
      });
    });
  });

})();
