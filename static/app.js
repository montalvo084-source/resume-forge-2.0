// ============================================================
// Tally Mark Renderer
// ============================================================

function renderTallyMarks(count, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (count === 0) {
    container.innerHTML = '<span class="text-gray-300 text-sm font-medium">Your first mark awaits...</span>';
    return;
  }

  const groups = Math.floor(count / 5);
  const remainder = count % 5;
  let html = '';

  for (let i = 0; i < groups; i++) {
    html += '<span class="tally-group">';
    html += '<span class="tally-vert">|</span>'.repeat(4);
    html += '<span class="tally-slash">/</span>';
    html += '</span>';
  }

  for (let i = 0; i < remainder; i++) {
    html += '<span class="tally-single">|</span>';
  }

  container.innerHTML = html;
}


// ============================================================
// Animated counter (counts up from 0 to target)
// ============================================================

function animateCounter(elementId, target) {
  const el = document.getElementById(elementId);
  if (!el || target === 0) return;

  const duration = 800;
  const start = performance.now();
  const startVal = 0;

  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(startVal + (target - startVal) * eased);
    el.textContent = current;
    el.classList.add('count-animate');
    if (progress < 1) requestAnimationFrame(update);
  }

  requestAnimationFrame(update);
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

  if (count === 75) {
    confetti({ particleCount: 200, spread: 100, colors: ['#7C3AED', '#FFD700', '#C4B5FD'], origin: { y: 0.6 } });
    setTimeout(() => confetti({ particleCount: 150, spread: 80, colors: ['#7C3AED', '#A78BFA'], origin: { y: 0.5 } }), 500);
    _showMilestoneToast('💎 75 Applications — Elite Status!');
    return;
  }

  if (count === 50) {
    confetti({ particleCount: 120, angle: 60, spread: 80, origin: { x: 0, y: 0.8 } });
    confetti({ particleCount: 120, angle: 120, spread: 80, origin: { x: 1, y: 0.8 } });
    setTimeout(() => confetti({ particleCount: 80, spread: 120, origin: { y: 0.5 } }), 400);
    _showMilestoneToast('🔥 50 Applications — Unstoppable!');
    return;
  }

  if (count === 25) {
    confetti({ particleCount: 180, spread: 90, colors: ['#FFD700', '#FFA500', '#4ECDC4', '#FF6B6B'], origin: { y: 0.6 } });
    _showMilestoneToast('⚡ 25 Applications — On a Roll!');
    return;
  }

  if (count === 10) {
    confetti({ particleCount: 140, spread: 80, colors: ['#6366F1', '#818CF8', '#C7D2FE'], origin: { y: 0.6 } });
    _showMilestoneToast('📈 10 Deep — Building Momentum!');
    return;
  }

  if (count === 5) {
    confetti({ particleCount: 100, spread: 70, colors: ['#10B981', '#6EE7B7'], origin: { y: 0.6 } });
    _showMilestoneToast('🎯 First 5 — You\'re In the Game!');
    return;
  }

  // Every app — small satisfying burst
  confetti({
    particleCount: 55,
    spread: 45,
    colors: ['#6366F1', '#A78BFA', '#67E8F9'],
    origin: { y: 0.7 },
  });
}

function _epicConfetti() {
  const duration = 8000;
  const end = Date.now() + duration;

  (function frame() {
    confetti({
      particleCount: 14,
      angle: 60,
      spread: 55,
      origin: { x: 0, y: 0.6 },
      colors: ['#FFD700', '#FF6B6B', '#4ECDC4', '#6366F1', '#F59E0B'],
    });
    confetti({
      particleCount: 14,
      angle: 120,
      spread: 55,
      origin: { x: 1, y: 0.6 },
      colors: ['#FFD700', '#FF6B6B', '#4ECDC4', '#6366F1', '#F59E0B'],
    });
    if (Date.now() < end) requestAnimationFrame(frame);
  })();

  const overlay = document.getElementById('milestone-overlay');
  if (overlay) {
    overlay.classList.remove('hidden');
    setTimeout(() => overlay.classList.add('hidden'), 9000);
  }
}


// ============================================================
// Milestone Toast Notification
// ============================================================

function _showMilestoneToast(message) {
  // Remove any existing toast
  const existing = document.getElementById('milestone-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.id = 'milestone-toast';
  toast.innerHTML = `
    <div class="flex items-center gap-3">
      <span class="text-2xl">${message.split(' ')[0]}</span>
      <div>
        <div class="font-bold text-white text-sm">${message.split(' ').slice(1, -1).join(' ')}</div>
        <div class="text-indigo-200 text-xs">${message.split(' ').pop()}</div>
      </div>
    </div>
  `;
  toast.style.cssText = `
    position: fixed;
    top: 80px;
    left: 50%;
    transform: translateX(-50%) translateY(-20px);
    background: linear-gradient(135deg, #4338CA, #6D28D9);
    color: white;
    padding: 14px 20px;
    border-radius: 16px;
    box-shadow: 0 8px 30px rgba(79,70,229,0.5);
    z-index: 9999;
    opacity: 0;
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
    min-width: 260px;
    max-width: 90vw;
    text-align: left;
  `;
  document.body.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateX(-50%) translateY(0)';
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(-50%) translateY(-10px)';
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}
