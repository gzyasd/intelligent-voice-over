const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const exePath = process.argv[2] || path.join(__dirname, '..', 'dist2', 'win-unpacked', 'resources', 'python', 'ivo-server.exe');
console.log('exePath:', exePath);
console.log('exists:', fs.existsSync(exePath));

const proc = spawn(exePath, ['17020'], {
  windowsHide: true,
  stdio: ['ignore', 'pipe', 'pipe'],
});

proc.stdout.on('data', (data) => console.log('stdout:', data.toString()));
proc.stderr.on('data', (data) => console.error('stderr:', data.toString()));
proc.on('error', (err) => console.error('spawn error:', err));
proc.on('exit', (code, signal) => console.log('exit:', code, signal));

setTimeout(() => {
  console.log('killing');
  proc.kill();
  process.exit(0);
}, 5000);
