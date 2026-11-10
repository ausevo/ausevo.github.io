/* AES conference schedule — vanilla JS, no dependencies.
   Markup: _layouts/schedule.html · Data: _data/programme_YYYY.yml

   - Day tabs, room filter, "My talks" (stars saved in localStorage), search
   - "Now & Next" panel and an Outlook-style now-line, in conference time zone
   - Download starred talks as an .ics calendar file
   Testing: add ?now=2026-12-02T10:37 to the URL to pretend it is that time. */

(function () {
  'use strict';

  var root = document.querySelector('.schedule');
  if (!root) return;
  root.classList.add('is-js');

  var TZ    = root.dataset.tz || 'Australia/Sydney';
  var STORE = 'aes-schedule-stars-' + (root.dataset.year || '');
  var CONF  = root.dataset.conf || 'Conference';

  var $  = function (sel, ctx) { return (ctx || root).querySelector(sel); };
  var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || root).querySelectorAll(sel)); };

  var days     = $$('.sched-day');
  var dayBtns  = $$('.sched-days__btn');
  var roomBtns = $$('[data-room-filter]');
  var mineBtn  = $('.sched-mine');
  var mineCnt  = $('[data-mine-count]');
  var searchEl = $('[data-search]');
  var panel    = $('[data-now-panel]');
  var emptyEl  = $('[data-empty]');
  var actions  = $('[data-mine-actions]');
  var toolbar  = $('.sched-toolbar');

  // ─── Helpers ──────────────────────────────────────────────────────────────

  function toMin(hhmm) {
    var p = String(hhmm || '').split(':');
    return parseInt(p[0], 10) * 60 + parseInt(p[1] || 0, 10);
  }
  function fmt(min) {
    min = Math.floor(min);
    return ('0' + Math.floor(min / 60)).slice(-2) + ':' + ('0' + (min % 60)).slice(-2);
  }
  function norm(s) {
    s = String(s || '').toLowerCase();
    return s.normalize ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, '') : s;
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  // Cache times on every timed element
  $$('[data-start]').forEach(function (e) {
    e._s = toMin(e.dataset.start);
    e._e = e.dataset.end ? toMin(e.dataset.end) : e._s;
    var d = e.closest('.sched-day');
    e._date = d ? d.dataset.date : '';
  });
  // A row lasts until its longest item ends
  $$('[data-row]').forEach(function (r) {
    r._e = r._s;
    $$('[data-item]', r).forEach(function (i) { if (i._e > r._e) r._e = i._e; });
  });

  // ─── Clock (conference time zone) ─────────────────────────────────────────

  var params   = new URLSearchParams(location.search);
  var override = (params.get('now') || '').match(/^(\d{4}-\d{2}-\d{2})[T ](\d{1,2}):(\d{2})/);
  var loadedAt = Date.now();
  var dtf = null;
  try {
    dtf = new Intl.DateTimeFormat('en-CA', {
      timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
    });
  } catch (e) { /* very old browser: fall back to device time */ }

  function zoneParts(ts) {
    var o = {};
    if (dtf) {
      dtf.formatToParts(new Date(ts)).forEach(function (p) { o[p.type] = p.value; });
    } else {
      var d = new Date(ts);
      o = { year: d.getFullYear(), month: ('0' + (d.getMonth() + 1)).slice(-2), day: ('0' + d.getDate()).slice(-2),
            hour: d.getHours(), minute: d.getMinutes(), second: d.getSeconds() };
    }
    return o;
  }

  function now() {
    if (override) {
      var elapsed = (Date.now() - loadedAt) / 60000;   // let the test clock run
      return { date: override[1], min: parseInt(override[2], 10) * 60 + parseInt(override[3], 10) + elapsed };
    }
    var o = zoneParts(Date.now());
    return { date: o.year + '-' + o.month + '-' + o.day,
             min: (parseInt(o.hour, 10) % 24) * 60 + parseInt(o.minute, 10) + parseInt(o.second, 10) / 60 };
  }

  // Local conference time → UTC timestamp (for calendar export)
  function zonedToUtc(date, min) {
    var y = +date.slice(0, 4), m = +date.slice(5, 7) - 1, d = +date.slice(8, 10);
    var guess = Date.UTC(y, m, d, 0, min);
    function offset(ts) {
      var o = zoneParts(ts);
      return Date.UTC(+o.year, +o.month - 1, +o.day, +o.hour % 24, +o.minute, +o.second) - ts;
    }
    var utc = guess - offset(guess);
    return guess - offset(utc);
  }

  // ─── Stars ────────────────────────────────────────────────────────────────

  var starred = {};
  try {
    (JSON.parse(localStorage.getItem(STORE)) || []).forEach(function (id) { starred[id] = true; });
  } catch (e) { /* storage blocked: stars just won't persist */ }

  function saveStars() {
    try { localStorage.setItem(STORE, JSON.stringify(Object.keys(starred))); } catch (e) {}
  }

  function paintStar(item) {
    var on = !!starred[item.dataset.id];
    item.classList.toggle('is-starred', on);
    var speedCard = item.closest('.talk--speed');
    if (speedCard && speedCard !== item) {
      speedCard.classList.toggle('has-starred', !!speedCard.querySelector('.is-starred'));
    }
    var btn = item.querySelector('[data-star]');
    if (btn && btn.closest('[data-talk]') === item) {
      btn.setAttribute('aria-pressed', String(on));
      var who = btn.getAttribute('aria-label').replace(/^(Add to|Remove from) My talks/, '');
      btn.setAttribute('aria-label', (on ? 'Remove from' : 'Add to') + ' My talks' + who);
    }
  }

  function updateCount() {
    var n = $$('[data-talk]').filter(function (t) { return starred[t.dataset.id]; }).length;
    mineCnt.textContent = n ? String(n) : '';
  }

  $$('[data-talk]').forEach(paintStar);
  updateCount();

  // ─── View state + filtering ───────────────────────────────────────────────

  var state = { day: null, room: 'all', mine: false, q: '' };

  // ─── Compact phone layout: expand on tap ──────────────────────────────────
  // expandMode 'slot' = tapping a card opens the whole time slot (all rooms, full cards)
  //            'card' = tapping a card opens just that card, full width, below the row
  var MODE_KEY = 'aes-schedule-expand';
  var saved = null;
  try { saved = localStorage.getItem(MODE_KEY); } catch (e) {}
  var expandMode = (params.get('expand') || saved) === 'card' ? 'card' : 'slot';
  root.dataset.expand = expandMode;
  var mq = window.matchMedia ? window.matchMedia('(max-width: 767px)') : { matches: false };

  function isCompact() { return mq.matches && state.room === 'all' && !state.mine && !state.q; }

  function setOpen(cell, open) {
    var row = cell.closest('.sched-row');
    var cells = $$('.sched-cell', row);
    if (expandMode === 'slot') {
      cells.forEach(function (c) { c.classList.toggle('is-expanded', open); });
    } else {
      cells.forEach(function (c) { c.classList.remove('is-expanded'); });
      if (open) cell.classList.add('is-expanded');
    }
    row.classList.toggle('is-open', cells.some(function (c) { return c.classList.contains('is-expanded'); }));
    cells.forEach(function (c) {
      var t = c.querySelector('[data-toggle]');
      if (t) t.setAttribute('aria-expanded', String(c.classList.contains('is-expanded')));
    });
  }

  function collapseAll() {
    $$('.is-expanded').forEach(function (c) { c.classList.remove('is-expanded'); });
    $$('.sched-row.is-open').forEach(function (r) { r.classList.remove('is-open'); });
    $$('[data-toggle]').forEach(function (t) { t.setAttribute('aria-expanded', 'false'); });
  }

  function searchText(t) {
    if (t._text == null) t._text = norm(t.textContent + ' ' + (t.dataset.session || '') + ' ' + (t.dataset.room || ''));
    return t._text;
  }

  function matches(item, terms) {
    if (state.room !== 'all' && item.dataset.room !== 'all' && item.dataset.room !== state.room) return false;
    if (state.mine && !starred[item.dataset.id]) return false;
    for (var i = 0; i < terms.length; i++) if (searchText(item).indexOf(terms[i]) < 0) return false;
    return true;
  }

  function apply() {
    var terms = norm(state.q).split(/\s+/).filter(Boolean);
    var filtering = state.mine || terms.length > 0;
    root.classList.toggle('is-filtering', filtering);
    root.dataset.room = state.room;

    dayBtns.forEach(function (b) {
      b.setAttribute('aria-pressed', String(!filtering && b.dataset.day === state.day));
    });
    roomBtns.forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.roomFilter === state.room));
    });
    mineBtn.setAttribute('aria-pressed', String(state.mine));

    var shownTotal = 0;

    days.forEach(function (day) {
      if (!filtering) {
        // Normal view: one day, everything visible (room filter is pure CSS)
        $$('[hidden]', day).forEach(function (e) { e.hidden = false; });
        $$('.is-out', day).forEach(function (e) { e.classList.remove('is-out'); });
        day.hidden = day.dataset.date !== state.day;
        return;
      }

      var dayCount = 0;

      $$('[data-row]', day).forEach(function (row) {
        var rowShown = false;
        if (row.classList.contains('sched-row--event')) {
          var ev = row.querySelector('[data-item]');
          var isTalk = ev.hasAttribute('data-talk');
          // My talks keeps meals/socials for context; search must match text
          var context = ev.classList.contains('sched-event--break') || ev.classList.contains('sched-event--social');
          var ok = isTalk ? matches(ev, terms)
                          : (terms.length ? matches(ev, terms) && !state.mine : state.mine && context);
          rowShown = ok;
          if (ok && isTalk) dayCount++;
        } else {
          $$('.sched-cell', row).forEach(function (cell) {
            var cellShown = false;
            $$('[data-talk]', cell).forEach(function (t) {
              var ok = matches(t, terms);
              t.hidden = !ok;
              if (ok) { cellShown = true; dayCount++; }
            });
            cell.classList.toggle('is-out', !cellShown);
            if (cellShown) rowShown = true;
          });
        }
        row.hidden = !rowShown;
      });

      $$('.sched-block', day).forEach(function (b) {
        b.hidden = !$$('[data-row]', b).some(function (r) { return !r.hidden; });
      });

      day.hidden = dayCount === 0;
      shownTotal += dayCount;
    });

    // Empty-state message
    if (filtering && shownTotal === 0) {
      emptyEl.textContent = state.mine && !terms.length
        ? 'No starred talks yet. Tap the ☆ on any talk to add it to My talks.'
        : 'No talks match your search' + (state.mine ? ' in My talks' : '') + '.';
      emptyEl.hidden = false;
    } else {
      emptyEl.hidden = true;
    }
    if (actions) actions.hidden = !(state.mine && shownTotal > 0);

    writeUrl();
    tick();
  }

  function writeUrl() {
    var p = new URLSearchParams(location.search);
    ['day', 'room', 'mine', 'q', 'expand'].forEach(function (k) { p.delete(k); });
    p.delete('expand');   // the choice is remembered on the device, not in the URL
    if (state.day && state.day !== defaultDay()) p.set('day', state.day);
    if (state.room !== 'all') p.set('room', state.room);
    if (state.mine) p.set('mine', '1');
    if (state.q) p.set('q', state.q);
    var qs = p.toString();
    try { history.replaceState(null, '', location.pathname + (qs ? '?' + qs : '') + location.hash); } catch (e) {}
  }

  function defaultDay() {
    var today = now().date;
    if (days.some(function (d) { return d.dataset.date === today; })) return today;
    // Otherwise the first full conference day (skip workshop-only days)
    var main = days.filter(function (d) { return d.querySelector('.sched-block'); })[0] || days[0];
    return main ? main.dataset.date : null;
  }

  // ─── Now-line, "now" highlighting, Now & Next panel ───────────────────────

  function clearNow() {
    $$('.now-line, .talk__now, .now-progress').forEach(function (e) { e.parentNode.removeChild(e); });
    $$('.is-now, .is-past').forEach(function (e) { e.classList.remove('is-now', 'is-past'); });
  }

  function tick() {
    clearNow();
    var n = now();
    dayBtns.forEach(function (b) { b.classList.toggle('is-today', b.dataset.day === n.date); });

    var today = days.filter(function (d) { return d.dataset.date === n.date; })[0];
    if (!today) { panel.hidden = true; return; }

    // Rows: fade past ones, draw the line through the current one
    var lineDone = false;
    $$('[data-row]', today).forEach(function (row) {
      if (row._e <= n.min) row.classList.add('is-past');
      if (!lineDone && row._s <= n.min && n.min < row._e && !row.hidden) {
        var line = el('div', 'now-line');
        line.style.top = ((n.min - row._s) / (row._e - row._s) * 100).toFixed(2) + '%';
        line.setAttribute('aria-hidden', 'true');
        line.appendChild(el('span', 'now-line__label', fmt(n.min)));
        row.appendChild(line);
        lineDone = true;
      }
    });

    // Items happening now
    $$('[data-item]', today).forEach(function (it) {
      if (!(it._s <= n.min && n.min < it._e)) return;
      it.classList.add('is-now');
      if (it.classList.contains('talk--speed')) return;
      var dur = it._e - it._s, done = Math.floor(n.min - it._s);
      var tag = el('p', 'talk__now');
      var span = el('span', 'now-tag', 'Now');
      span.appendChild(el('span', 'now-tag__detail', ' · ' + done + ' of ' + dur + ' min'));
      tag.appendChild(span);
      var host = it.querySelector('.talk__text, .sched-event__body');
      if (host) host.insertBefore(tag, host.firstChild);
      if (!it.classList.contains('talk--mini')) {
        var bar = el('span', 'now-progress');
        bar.style.setProperty('--progress', (done / dur * 100).toFixed(1) + '%');
        bar.setAttribute('aria-hidden', 'true');
        it.appendChild(bar);
      }
    });

    renderPanel(today, n);
  }

  function itemSummary(it) {
    var sp = it.querySelector('.talk__speaker');
    var ti = it.querySelector('.talk__title, .sched-event__title');
    var label = it.querySelector('.sched-event__label');
    return {
      speaker: sp ? sp.firstChild && sp.firstChild.nodeType === 3 ? sp.firstChild.textContent.trim() : sp.textContent.trim() : (label ? label.textContent.trim() : ''),
      titleHTML: ti ? ti.innerHTML : ''
    };
  }

  function panelItem(it) {
    var a = el('a', 'now-item');
    a.href = '#' + it.id;
    if (it.dataset.room && it.dataset.room !== 'all') {
      a.appendChild(el('span', 'room-chip room-chip--' + it.dataset.room, it.dataset.room.replace('r', '')));
    } else {
      var icon = it.querySelector('.sched-event__icon i');
      a.appendChild(icon ? icon.cloneNode(true) : el('span'));
    }
    var s = itemSummary(it);
    var text = el('span', 'now-item__text');
    if (s.speaker) text.appendChild(el('span', 'now-item__speaker', s.speaker));
    var t = el('span', 'now-item__title');
    t.innerHTML = s.titleHTML;   // site-generated markup (may contain <em>)
    text.appendChild(t);
    text.appendChild(el('span', 'now-item__time', fmt(it._s) + '–' + fmt(it._e) +
      (it.dataset.room && it.dataset.room !== 'all' ? ' · Room ' + it.dataset.room.replace('r', '') : '')));
    a.appendChild(text);
    var li = el('li');
    li.appendChild(a);
    return li;
  }

  function byRoom(a, b) { return (a.dataset.room === 'all' ? '' : a.dataset.room).localeCompare(b.dataset.room === 'all' ? '' : b.dataset.room); }

  function renderPanel(today, n) {
    // Candidates: individual talks + whole-conference events (not speed containers)
    var items = $$('[data-talk], .sched-event', today);
    if (!items.length) { panel.hidden = true; return; }
    var last = Math.max.apply(null, items.map(function (i) { return i._e; }));
    if (n.min >= last) { panel.hidden = true; return; }

    var onNow = items.filter(function (i) { return i._s <= n.min && n.min < i._e; }).sort(byRoom);
    var upcoming = items.filter(function (i) { return i._s > n.min; });
    var nextStart = upcoming.length ? Math.min.apply(null, upcoming.map(function (i) { return i._s; })) : null;
    var next = upcoming.filter(function (i) { return i._s === nextStart; }).sort(byRoom);

    panel.innerHTML = '';
    var head = el('div', 'now-panel__head');
    var clock = el('p', 'now-panel__clock');
    clock.appendChild(el('span', 'now-panel__dot'));
    clock.appendChild(document.createTextNode('Now ' + fmt(n.min)));
    head.appendChild(clock);
    var jump = el('button', 'sched-chip-btn', 'Jump to now ↓');
    jump.type = 'button';
    jump.addEventListener('click', jumpToNow);
    head.appendChild(jump);
    panel.appendChild(head);

    var grid = el('div', 'now-panel__grid');
    [['On now', onNow, 'Nothing scheduled right now.'],
     [nextStart != null ? 'Next · ' + fmt(nextStart) : 'Next', next, 'That’s it for today.']].forEach(function (c) {
      var col = el('div', 'now-panel__col');
      col.appendChild(el('h3', null, c[0]));
      if (c[1].length) {
        var ul = el('ul', 'now-panel__list');
        c[1].forEach(function (i) { ul.appendChild(panelItem(i)); });
        col.appendChild(ul);
      } else {
        col.appendChild(el('p', 'now-panel__none', c[2]));
      }
      grid.appendChild(col);
    });
    panel.appendChild(grid);
    panel.hidden = false;
  }

  // ─── Navigation helpers ───────────────────────────────────────────────────

  function showItem(target) {
    if (!target) return;
    var day = target.closest('.sched-day');
    if (target.hidden || (day && day.hidden) || (target.closest('[hidden]'))) {
      state.mine = false; state.q = ''; searchEl.value = '';
      if (state.room !== 'all' && target.dataset.room !== state.room) state.room = 'all';
    }
    if (day) state.day = day.dataset.date;
    apply();
    if (isCompact()) {
      var tc = target.closest('.sched-cell');
      if (tc && tc.closest('.sched-row--slot') && !tc.classList.contains('is-expanded')) setOpen(tc, true);
    }
    target.scrollIntoView({ block: 'center' });
    target.classList.add('is-flash');
    setTimeout(function () { target.classList.remove('is-flash'); }, 1600);
  }

  function jumpToNow() {
    var n = now();
    if (state.day !== n.date || state.mine || state.q) {
      state.day = n.date; state.mine = false; state.q = ''; searchEl.value = '';
      apply();
    }
    var line = $('.now-line');
    (line ? line.parentNode : panel).scrollIntoView({ block: 'center' });
  }

  // ─── Calendar export ──────────────────────────────────────────────────────

  function icsEscape(s) { return String(s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n'); }
  function icsDate(ts) { return new Date(ts).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, ''); }
  function fold(line) {
    var out = [];
    while (line.length > 73) { out.push(line.slice(0, 73)); line = ' ' + line.slice(73); }
    out.push(line);
    return out.join('\r\n');
  }

  function downloadIcs() {
    var stamp = icsDate(Date.now());
    var lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Australasian Evolution Society//Schedule//EN',
                 'CALSCALE:GREGORIAN', 'X-WR-CALNAME:' + icsEscape(CONF + ' – My talks')];
    $$('[data-talk]').filter(function (t) { return starred[t.dataset.id]; }).forEach(function (t) {
      var s = itemSummary(t);
      var title = (s.titleHTML ? s.titleHTML.replace(/<[^>]+>/g, '') : '');
      var tmp = document.createElement('textarea'); tmp.innerHTML = title; title = tmp.value;
      var room = t.dataset.room && t.dataset.room !== 'all' ? 'Room ' + t.dataset.room.replace('r', '') : '';
      var loc = t.querySelector('.sched-event__loc');
      lines.push('BEGIN:VEVENT',
        'UID:' + t.dataset.id + '@ausevo.github.io',
        'DTSTAMP:' + stamp,
        'DTSTART:' + icsDate(zonedToUtc(t._date, t._s)),
        'DTEND:' + icsDate(zonedToUtc(t._date, t._e)),
        fold('SUMMARY:' + icsEscape((s.speaker ? s.speaker + ': ' : '') + title)),
        fold('LOCATION:' + icsEscape([room || (loc ? loc.textContent.trim() : ''), 'University of Wollongong'].filter(Boolean).join(', '))),
        fold('DESCRIPTION:' + icsEscape((t.dataset.session || '') + '\n' + location.origin + location.pathname + '#' + t.id)),
        'END:VEVENT');
    });
    lines.push('END:VCALENDAR');
    var blob = new Blob([lines.join('\r\n') + '\r\n'], { type: 'text/calendar;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = '2026-AES-talks-' + (root.dataset.year || 'conference') + '.ics';
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.parentNode.removeChild(a); }, 1000);
  }

  // ─── Events ───────────────────────────────────────────────────────────────

  root.addEventListener('click', function (e) {
    var star = e.target.closest('[data-star]');
    if (star) {
      var item = star.closest('[data-talk]');
      var id = item.dataset.id;
      if (starred[id]) delete starred[id]; else starred[id] = true;
      saveStars();
      paintStar(item);
      updateCount();
      star.classList.add('is-popping');
      setTimeout(function () { star.classList.remove('is-popping'); }, 150);
      if (state.mine) apply();
      return;
    }
    var link = e.target.closest('a[href^="#t-"]');
    if (link) {
      e.preventDefault();
      var target = document.getElementById(link.getAttribute('href').slice(1));
      try { history.replaceState(null, '', link.getAttribute('href')); } catch (err) {}
      showItem(target);
      return;
    }
    var tg = e.target.closest('[data-toggle]');
    if (tg) {
      var tcell = tg.closest('.sched-cell');
      setOpen(tcell, !tcell.classList.contains('is-expanded'));
      return;
    }
    if (e.target.closest('[data-ics]')) downloadIcs();
  });

  dayBtns.forEach(function (b) {
    b.addEventListener('click', function () {
      state.day = b.dataset.day;
      state.mine = false; state.q = ''; searchEl.value = '';
      apply();
      // If scrolled down into the old day, go back to the top of the schedule
      var navH = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--nav-h'), 10) || 0;
      var top = root.getBoundingClientRect().top + window.pageYOffset - navH;
      if (window.pageYOffset > top) window.scrollTo(0, top);
    });
  });

  roomBtns.forEach(function (b) {
    b.addEventListener('click', function () { state.room = b.dataset.roomFilter; apply(); });
  });

  var modeBtns = $$('[data-expand-mode]');
  modeBtns.forEach(function (b) {
    b.setAttribute('aria-pressed', String(b.dataset.expandMode === expandMode));
    b.addEventListener('click', function () {
      expandMode = b.dataset.expandMode;
      root.dataset.expand = expandMode;
      modeBtns.forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      try { localStorage.setItem(MODE_KEY, expandMode); } catch (e) {}
      collapseAll();
      writeUrl();
    });
  });

  mineBtn.addEventListener('click', function () { state.mine = !state.mine; apply(); });

  var searchTimer;
  var searchBox = searchEl.closest('.sched-search');
  function paintSearch() { if (searchBox) searchBox.classList.toggle('has-q', searchEl.value.trim() !== ''); }
  searchEl.addEventListener('input', function () {
    paintSearch();
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () { state.q = searchEl.value.trim(); apply(); }, 120);
  });

  window.addEventListener('hashchange', function () {
    var t = location.hash && document.getElementById(location.hash.slice(1));
    if (t && t.closest('.schedule')) showItem(t);
  });

  function measureToolbar() {
    root.style.setProperty('--sched-toolbar-h', (toolbar ? toolbar.offsetHeight : 0) + 'px');
  }
  window.addEventListener('resize', measureToolbar);
  // The toolbar grows when the phone search box expands
  if (toolbar && window.ResizeObserver) new ResizeObserver(measureToolbar).observe(toolbar);

  // ─── Start ────────────────────────────────────────────────────────────────

  var validDay = function (d) { return days.some(function (x) { return x.dataset.date === d; }); };
  state.day  = validDay(params.get('day')) ? params.get('day') : defaultDay();
  state.room = roomBtns.some(function (b) { return b.dataset.roomFilter === params.get('room'); }) ? params.get('room') : 'all';
  state.mine = params.get('mine') === '1';
  state.q    = params.get('q') || '';
  searchEl.value = state.q;
  paintSearch();

  measureToolbar();
  apply();

  var initial = location.hash && document.getElementById(location.hash.slice(1));
  if (initial && initial.closest('.schedule')) showItem(initial);

  setInterval(tick, 30000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) tick(); });

})();
