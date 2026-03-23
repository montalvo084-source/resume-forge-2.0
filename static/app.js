// ============================================================
// Tally Mark Renderer
// ============================================================

function renderTallyMarks(count, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const groups = Math.floor(count / 5);
  const remainder = count % 5;
  let html = '';

  for (let i = 0; i < groups; i++) {
    html += '<span class="tally-group">';
    // 4 vertical marks + diagonal slash via CSS
    html += '<span class="tally-vert">|</span>'.repeat(4);
    html += '<span class="tally-slash">/</span>';
    html += '</span>';
  }

  for (let i = 0; i < remainder; i++) {
    html += '<span class="tally-single">|</span>';
  }

  if (count === 0) {
    html = '<span class="text-gray-300 text-sm">No applications yet</span>';
  }

  container.innerHTML = html;
}


// ============================================================
// Confetti System
// ============================================================

const MILESTONES = [5, 10, 25, 50, 75, 100];

function fireConfetti(count) {
  if (count === 100) {
    _epicConfetti();
    return;
  }

  const isMilestone = MILESTONES.includes(count);

  if (count === 75) {
    confetti({
      particleCount: 200,
      spread: 100,
      colors: ['#7C3AED', '#FFD700', '#C4B5FD'],
      origin: { y: 0.6 },
    });
    setTimeout(() => confetti({ particleCount: 150, spread: 80, colors: ['#7C3AED', '#A78BFA'], origin: { y: 0.5 } }), 600);
  } else if (count === 50) {
    // Fireworks style
    confetti({ particleCount: 100, angle: 60, spread: 80, origin: { x: 0, y: 0.8 } });
    confetti({ particleCount: 100, angle: 120, spread: 80, origin: { x: 1, y: 0.8 } });
    setTimeout(() => {
      confetti({ particleCount: 80, spread: 120, origin: { y: 0.5 } });
    }, 400);
  } else if (count === 25) {
    confetti({
      particleCount: 180,
      spread: 90,
      colors: ['#FFD700', '#FFA500', '#4ECDC4', '#FF6B6B'],
      origin: { y: 0.6 },
    });
  } else if (isMilestone) {
    // 5 or 10
    confetti({
      particleCount: 120,
      spread: 80,
      colors: ['#6366F1', '#818CF8', '#C7D2FE'],
      origin: { y: 0.6 },
    });
  } else {
    // Every app
    confetti({
      particleCount: 60,
      spread: 50,
      colors: ['#6366F1', '#A78BFA', '#67E8F9'],
      origin: { y: 0.7 },
    });
  }
}

function _epicConfetti() {
  const duration = 8000;
  const end = Date.now() + duration;

  (function frame() {
    confetti({
      particleCount: 12,
      angle: 60,
      spread: 55,
      origin: { x: 0, y: 0.6 },
      colors: ['#FFD700', '#FF6B6B', '#4ECDC4', '#6366F1', '#F59E0B'],
    });
    confetti({
      particleCount: 12,
      angle: 120,
      spread: 55,
      origin: { x: 1, y: 0.6 },
      colors: ['#FFD700', '#FF6B6B', '#4ECDC4', '#6366F1', '#F59E0B'],
    });
    if (Date.now() < end) {
      requestAnimationFrame(frame);
    }
  })();

  // Show motivational overlay
  const overlay = document.getElementById('milestone-overlay');
  if (overlay) {
    overlay.classList.remove('hidden');
    setTimeout(() => overlay.classList.add('hidden'), 9000);
  }
}


// ============================================================
// Clipboard copy helper (used in result.html inline)
// ============================================================

// copyResumeText() is defined inline in result.html since it needs
// access to the page-specific textarea element.
