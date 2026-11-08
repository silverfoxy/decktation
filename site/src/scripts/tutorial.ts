import overlays from '../../public/assets/app-overlays/manifest.json';

const lessons = [...document.querySelectorAll<HTMLElement>('.tutorial-lesson')];
const choices = [...document.querySelectorAll<HTMLButtonElement>('.tutorial-choice')];
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
let active = lessons[0];
let timer: ReturnType<typeof setTimeout> | undefined;
let phase = 'ready';
let animationFrame = 0;
let elapsed = 0;
let lastFrame = 0;
const player = () => active.querySelector<HTMLElement>('.tutorial-player')!;
const play = () => active.querySelector<HTMLButtonElement>('.tutorial-play')!;
function stop() {
  clearTimeout(timer); timer = undefined;
  cancelAnimationFrame(animationFrame); lastFrame = 0;
}
function nativeOverlay(name: keyof typeof overlays.dimensions, frame = 0) {
  const svg = active.querySelector<SVGSVGElement>('[data-native-overlay]')!;
  svg.removeAttribute('hidden');
  svg.setAttribute('viewBox', overlays.dimensions[name].viewBox);
  svg.dataset.kind = name;
  const labels = { recording: 'Recording', transcribing: 'Transcribing...', review: 'Review transcription: ready when you are. Party. Tap L1+R1 to send, hold to cancel.', sent: 'Sent', cancelled: 'Cancelled', typed: 'Typed into chat' };
  svg.setAttribute('aria-label', labels[name]);
  svg.querySelector('use')!.setAttribute('href', `/assets/app-overlays/sprite.svg#${name === 'recording' ? `recording-${frame}` : name}`);
}
function animate(time: number) {
  elapsed += lastFrame ? time - lastFrame : 0;
  lastFrame = time;
  nativeOverlay('recording', Math.floor((elapsed % overlays.periodMs) / overlays.periodMs * overlays.frames));
  animationFrame = requestAnimationFrame(animate);
}
function startAnimation() {
  cancelAnimationFrame(animationFrame); lastFrame = 0;
  if (phase === 'recording' && !reduced.matches) animationFrame = requestAnimationFrame(animate);
}
function render(next: string) {
  cancelAnimationFrame(animationFrame); lastFrame = 0;
  phase = next;
  player().dataset.phase = phase;
  const review = active.dataset.review === 'true';
  const messages: Record<string, string> = {
    ready: 'Ready when you are.', recording: 'Holding L1 + R1. Listening…',
    transcribing: 'Buttons released. Transcribing on your device…',
    done: review ? 'Review your transcript. Send it or cancel below.' : 'Your text is in place.',
    sent: 'Transcript sent.', cancelled: 'Transcript cancelled. Nothing was sent.',
  };
  active.querySelector('.tutorial-status')!.textContent = messages[phase];
  play().textContent = ['recording', 'transcribing'].includes(phase) ? 'Pause' : 'Replay example';
  const actions = active.querySelector<HTMLElement>('.tutorial-review-actions');
  if (actions) actions.hidden = phase !== 'done';
  if (phase === 'ready') active.querySelector('[data-native-overlay]')!.setAttribute('hidden', '');
  else if (phase === 'recording') { nativeOverlay('recording'); startAnimation(); }
  else if (phase === 'transcribing') nativeOverlay('transcribing');
  else if (phase === 'done') nativeOverlay(review ? 'review' : active.dataset.result === 'typed' ? 'typed' : 'sent');
  else nativeOverlay(phase === 'sent' ? 'sent' : 'cancelled');
}
function advance() {
  render(phase === 'recording' ? 'transcribing' : 'done');
  if (phase === 'transcribing') timer = setTimeout(advance, 1200);
  else stop();
}
function pause() { stop(); play().textContent = 'Resume'; }
choices.forEach(choice => choice.addEventListener('click', () => {
  stop();
  lessons.forEach(lesson => lesson.hidden = lesson.id !== `lesson-${choice.dataset.tutorial}`);
  choices.forEach(button => button.setAttribute('aria-pressed', String(button === choice)));
  active = lessons.find(lesson => !lesson.hidden)!;
  elapsed = 0; render('ready'); play().textContent = 'Play example';
}));
lessons.forEach(lesson => {
  lesson.querySelector('.tutorial-play')!.addEventListener('click', () => {
    if (timer) { pause(); return; }
    if (reduced.matches) { render('done'); return; }
    if (!['recording', 'transcribing'].includes(phase)) render('recording');
    else play().textContent = 'Pause';
    startAnimation();
    timer = setTimeout(advance, phase === 'recording' ? 2800 : 1200);
  });
  lesson.querySelector('.tutorial-reset')!.addEventListener('click', () => {
    stop(); elapsed = 0; render('ready'); play().textContent = 'Play example';
  });
  lesson.querySelector('.tutorial-send')?.addEventListener('click', () => render('sent'));
  lesson.querySelector('.tutorial-cancel')?.addEventListener('click', () => render('cancelled'));
});
document.addEventListener('visibilitychange', () => { if (document.hidden && timer) pause(); });
new IntersectionObserver(entries => {
  if (!entries[0].isIntersecting && timer) pause();
}, { threshold: 0.1 }).observe(document.querySelector('.tutorial-section')!);
reduced.addEventListener('change', () => { if (reduced.matches && timer) { stop(); render('done'); } });
