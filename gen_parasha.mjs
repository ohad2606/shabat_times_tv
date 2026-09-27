// Generate a Shabbat -> parasha table using @hebcal/core, for the Israel schedule.
// Run at build time; the page only does a lookup, so no calendar maths ships to the TV.
import { HebrewCalendar, HDate, flags } from '@hebcal/core';

const YEARS = Number(process.argv[2] || 12);
const start = new Date();
start.setMonth(start.getMonth() - 1);   // a little history, so today is always covered
const end = new Date(start); end.setFullYear(start.getFullYear() + YEARS);

const events = HebrewCalendar.calendar({
  start, end,
  il: true,            // Tel Aviv -> Israel schedule (differs from Diaspora some years)
  sedrot: true,
  noHolidays: true,
  locale: 'he',
});

const table = {};
for (const ev of events) {
  if (!(ev.getFlags() & flags.PARSHA_HASHAVUA)) continue;
  const d = ev.getDate().greg();
  const iso = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  // Strip nikkud (keeping U+05BE maqaf, which joins double portions like מטות־מסעי),
  // then drop the "פרשת" prefix -- which only matches once the nikkud is gone.
  table[iso] = ev.render('he')
    .replace(/[\u0591-\u05BD\u05BF-\u05C7]/g, '')
    .replace(/^פרשת\s+/, '')
    .trim();
}
const keys = Object.keys(table).sort();
console.error(`${keys.length} shabbatot, ${keys[0]} .. ${keys[keys.length-1]}`);
console.log(JSON.stringify(table));
