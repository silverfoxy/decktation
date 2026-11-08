const lessons = [...document.querySelectorAll<HTMLElement>('.tutorial-lesson')];
const choices = [...document.querySelectorAll<HTMLButtonElement>('.tutorial-choice')];
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
let active = lessons[0];
let timer: ReturnType<typeof setTimeout> | undefined;
let phase = 'ready';
const player = () => active.querySelector<HTMLElement>('.tutorial-player')!;
const play = () => active.querySelector<HTMLButtonElement>('.tutorial-play')!;
function stop() { clearTimeout(timer); timer = undefined; }
function render(next: string) {
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
}
function advance() {
  render(phase === 'recording' ? 'transcribing' : 'done');
  if (phase === 'transcribing') timer = setTimeout(advance, 1200);
  else stop();
}
function pause() { stop(); player().classList.add('tutorial-paused'); play().textContent = 'Resume'; }
choices.forEach(choice => choice.addEventListener('click', () => {
  stop();
  lessons.forEach(lesson => lesson.hidden = lesson.id !== `lesson-${choice.dataset.tutorial}`);
  choices.forEach(button => button.setAttribute('aria-pressed', String(button === choice)));
  active = lessons.find(lesson => !lesson.hidden)!;
  player().classList.remove('tutorial-paused');
  render('ready'); play().textContent = 'Play example';
}));
lessons.forEach(lesson => {
  lesson.querySelector('.tutorial-play')!.addEventListener('click', () => {
    if (timer) { pause(); return; }
    player().classList.remove('tutorial-paused');
    if (reduced.matches) { render('done'); return; }
    if (!['recording', 'transcribing'].includes(phase)) render('recording');
    else play().textContent = 'Pause';
    timer = setTimeout(advance, phase === 'recording' ? 2800 : 1200);
  });
  lesson.querySelector('.tutorial-reset')!.addEventListener('click', () => {
    stop(); player().classList.remove('tutorial-paused'); render('ready'); play().textContent = 'Play example';
  });
  lesson.querySelector('.tutorial-send')?.addEventListener('click', () => render('sent'));
  lesson.querySelector('.tutorial-cancel')?.addEventListener('click', () => render('cancelled'));
});
document.addEventListener('visibilitychange', () => { if (document.hidden && timer) pause(); });
new IntersectionObserver(entries => {
  if (!entries[0].isIntersecting && timer) pause();
}, { threshold: 0.1 }).observe(document.querySelector('.tutorial-section')!);
reduced.addEventListener('change', () => { if (reduced.matches && timer) { stop(); render('done'); } });
