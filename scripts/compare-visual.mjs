// Порівнює два набори знімків і падає, якщо вигляд справді змінився.
// Запуск: node scripts/compare-visual.mjs <еталон> <новий>
//
// Порівнювати на точну рівність марно: згладжування шрифтів і зведення
// близьких відтінків зсувають кольори на 1-4 одиниці з 255, чого око не
// бачить, але формальна перевірка вважає зміною кожен піксель. Тому
// рахується ВЕЛИЧИНА відхилення на канал, а не сам факт відмінності.
import { readdirSync, readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { PNG } from 'pngjs';

const [baseDir = '.local-tools/visual/baseline', newDir = '.local-tools/visual/after'] =
  process.argv.slice(2);

// Відхилення до цього значення на канал вважається непомітним.
const DELTA = Number(process.env.VISUAL_DELTA ?? 8);
// Частка помітно змінених пікселів, вище якої це вже регресія, а не шум.
const SHARE = Number(process.env.VISUAL_SHARE ?? 0.05);

let failed = 0;
let missing = 0;
const files = readdirSync(baseDir)
  .filter((f) => f.endsWith('.png'))
  .sort();

for (const file of files) {
  const newPath = path.join(newDir, file);
  if (!existsSync(newPath)) {
    console.log(`ВІДСУТНІЙ   ${file}`);
    missing += 1;
    continue;
  }
  const a = PNG.sync.read(readFileSync(path.join(baseDir, file)));
  const b = PNG.sync.read(readFileSync(newPath));

  if (a.width !== b.width || a.height !== b.height) {
    console.log(`РОЗМІР      ${file}: ${a.width}x${a.height} -> ${b.width}x${b.height}`);
    failed += 1;
    continue;
  }

  let loud = 0;
  let maxDelta = 0;
  for (let i = 0; i < a.data.length; i += 4) {
    const d = Math.max(
      Math.abs(a.data[i] - b.data[i]),
      Math.abs(a.data[i + 1] - b.data[i + 1]),
      Math.abs(a.data[i + 2] - b.data[i + 2]),
      Math.abs(a.data[i + 3] - b.data[i + 3]),
    );
    if (d > maxDelta) maxDelta = d;
    if (d > DELTA) loud += 1;
  }

  if (!maxDelta) continue;
  const share = (loud / (a.width * a.height)) * 100;
  const summary = `${file}: помітних ${loud} (${share.toFixed(3)}%), найбільше відхилення ${maxDelta}`;
  if (share > SHARE) {
    console.log(`РЕГРЕСІЯ    ${summary}`);
    failed += 1;
  } else {
    console.log(`у межах     ${summary}`);
  }
}

console.log(
  `\nпорівняно ${files.length}, без регресій ${files.length - failed - missing}, регресій ${failed}, відсутніх ${missing}`,
);
if (failed || missing) process.exit(1);
