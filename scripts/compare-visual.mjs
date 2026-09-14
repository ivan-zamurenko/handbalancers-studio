// Порівнює два набори знімків попіксельно.
// Запуск: node scripts/compare-visual.mjs <еталон> <новий>
// Код виходу 1, якщо є хоч одна відмінність - щоб рефакторинг стилів не міг
// тихо змінити вигляд сторінки.
import { readdirSync, readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { PNG } from 'pngjs';

const [baseDir = '.local-tools/visual/baseline', newDir = '.local-tools/visual/after'] =
  process.argv.slice(2);

// Згладжування шрифтів і анімації дають одиничні пікселі різниці навіть на
// незмінному коді, тому поріг у частках відсотка відсіює шум, а не регресії.
const NOISE_SHARE = Number(process.env.VISUAL_NOISE_SHARE ?? 0.05);

let differing = 0;
let missing = 0;

for (const file of readdirSync(baseDir)
  .filter((f) => f.endsWith('.png'))
  .sort()) {
  const newPath = path.join(newDir, file);
  if (!existsSync(newPath)) {
    console.log(`ВІДСУТНІЙ  ${file}`);
    missing += 1;
    continue;
  }
  const a = PNG.sync.read(readFileSync(path.join(baseDir, file)));
  const b = PNG.sync.read(readFileSync(newPath));

  if (a.width !== b.width || a.height !== b.height) {
    console.log(`РОЗМІР     ${file}: ${a.width}x${a.height} -> ${b.width}x${b.height}`);
    differing += 1;
    continue;
  }

  let diff = 0;
  for (let i = 0; i < a.data.length; i += 4) {
    if (
      a.data[i] !== b.data[i] ||
      a.data[i + 1] !== b.data[i + 1] ||
      a.data[i + 2] !== b.data[i + 2] ||
      a.data[i + 3] !== b.data[i + 3]
    ) {
      diff += 1;
    }
  }
  if (diff) {
    const share = (diff / (a.width * a.height)) * 100;
    if (share > NOISE_SHARE) {
      console.log(`ВІДМІННІСТЬ ${file}: ${diff} пікселів (${share.toFixed(3)}%)`);
      differing += 1;
    } else {
      console.log(`шум        ${file}: ${diff} пікселів (${share.toFixed(3)}%) - у межах порога`);
    }
  }
}

const total = readdirSync(baseDir).filter((f) => f.endsWith('.png')).length;
console.log(
  `\nпорівняно ${total}, ідентичних ${total - differing - missing}, відмінних ${differing}, відсутніх ${missing}`,
);
if (differing || missing) process.exit(1);
