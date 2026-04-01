/** Get the VectorBrain base directory (~/.vectorbrain) */
export declare function getVbDir(): string;
export declare function ensureDir(dir: string): Promise<void>;
export declare function readJson<T>(filePath: string): Promise<T | null>;
export declare function writeJson(filePath: string, data: unknown): Promise<void>;
export declare function listFiles(dir: string, ext: string): Promise<string[]>;
export declare function sleep(ms: number): Promise<void>;
export declare function timestamp(): string;
//# sourceMappingURL=utils.d.ts.map