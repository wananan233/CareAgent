import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

/**
 * 日志脱敏红线（任务书 8.1 / 9）：日志只允许 correlation_id / route / reason_code /
 * duration；禁止把消息正文、身份字段、Token 或健康数据写入日志或本地存储。
 * 本测试静态扫描 src，断言源码中不存在 console 敏感日志与浏览器存储写入。
 */

const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../src');

function collectSourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      out.push(...collectSourceFiles(full));
    } else if (/\.(ts|vue)$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}

function scan(pattern: RegExp): string[] {
  return collectSourceFiles(srcRoot).filter((file) => {
    const text = readFileSync(file, 'utf8');
    return pattern.test(text);
  });
}

describe('日志脱敏检查（静态扫描）', () => {
  it('源码中不存在 console 日志（不落任何日志）', () => {
    const files = scan(/\bconsole\.(log|error|warn|info|debug|trace)\b/);
    expect(files, `发现 console 日志：\n${files.join('\n')}`).toEqual([]);
  });

  it('源码中不写入 localStorage / sessionStorage / IndexedDB', () => {
    const files = scan(/\b(localStorage|sessionStorage|indexedDB)\b/);
    expect(files, `发现浏览器存储写入：\n${files.join('\n')}`).toEqual([]);
  });

  it('源码中不出现凭据/密钥敏感标识', () => {
    const files = scan(
      /\b(Bearer|Authorization|access[_-]?token|api[_-]?key|client[_-]?secret|private[_-]?key|password)\b/i,
    );
    expect(files, `发现凭据/密钥标识：\n${files.join('\n')}`).toEqual([]);
  });
});
