let audioContext = null;
let oscillator = null;
let gain = null;
let toneTimer = null;
let playing = false;

const TONES = [620, 840];

function buildContext() {
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) return null;
  if (!audioContext) audioContext = new AudioContext();
  return audioContext;
}

export function startSiren() {
  const context = buildContext();
  if (!context) return false;
  context.resume().catch(() => {});

  if (playing) return true;

  oscillator = context.createOscillator();
  gain = context.createGain();
  oscillator.type = 'sawtooth';
  oscillator.frequency.value = TONES[0];
  gain.gain.value = 0.035;
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start();
  playing = true;

  let toneIndex = 0;
  toneTimer = window.setInterval(() => {
    if (!oscillator) return;
    toneIndex = (toneIndex + 1) % TONES.length;
    oscillator.frequency.setTargetAtTime(TONES[toneIndex], context.currentTime, 0.035);
  }, 560);

  return true;
}

export function stopSiren() {
  if (toneTimer) window.clearInterval(toneTimer);
  toneTimer = null;
  if (oscillator) {
    try {
      oscillator.stop();
    } catch {
      // The oscillator may already be stopped when the page is being torn down.
    }
    oscillator.disconnect();
    oscillator = null;
  }
  if (gain) {
    gain.disconnect();
    gain = null;
  }
  playing = false;
}

export function isSirenPlaying() {
  return playing;
}
