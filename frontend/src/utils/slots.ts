function format12(hour24: number, minute: number): string {
  const ampm = hour24 < 12 ? 'AM' : 'PM';
  const h12 = hour24 % 12 === 0 ? 12 : hour24 % 12;
  const mm = minute === 0 ? '00' : '30';
  return `${h12}:${mm} ${ampm}`;
}

export const WORK_TIME_SLOTS: string[] = (() => {
  const out: string[] = [];
  for (let mins = 9 * 60; mins <= 17 * 60 + 30; mins += 30) {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    if (h >= 18) break;
    out.push(format12(h, m));
  }
  return out;
})();
