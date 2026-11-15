import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const lcovPath = path.resolve(__dirname, '../coverage/lcov.info');

if (fs.existsSync(lcovPath)) {
  const content = fs.readFileSync(lcovPath, 'utf8');
  const updated = content.replace(/^SF:src\//gm, 'SF:frontend/src/');
  fs.writeFileSync(lcovPath, updated, 'utf8');
  console.log('Adjusted lcov.info paths for SonarQube (SF:src/ -> SF:frontend/src/)');
}

