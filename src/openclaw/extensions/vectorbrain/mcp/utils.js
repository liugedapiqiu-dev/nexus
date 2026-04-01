/**
 * VectorBrain Utilities
 */
import fs from 'fs';
import path from 'path';
/** Get the VectorBrain base directory (~/.vectorbrain) */
export function getVbDir() {
    return path.join(process.env.HOME || '/tmp', '.vectorbrain');
}
export async function ensureDir(dir) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}
export async function readJson(filePath) {
    if (!fs.existsSync(filePath))
        return null;
    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        return JSON.parse(content);
    }
    catch {
        return null;
    }
}
export async function writeJson(filePath, data) {
    await ensureDir(path.dirname(filePath));
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
}
export async function listFiles(dir, ext) {
    if (!fs.existsSync(dir))
        return [];
    return fs.readdirSync(dir)
        .filter(f => f.endsWith(ext))
        .map(f => path.join(dir, f));
}
export function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
export function timestamp() {
    return new Date().toISOString();
}
//# sourceMappingURL=utils.js.map