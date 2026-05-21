const BULLET_PREFIX = /^[\s•\-–—*]+/;
const NUMBERED_PREFIX = /^\s*\d+[.)]\s+/;

/** Split prose into short leadership bullets when structured bullet_points are absent. */
export function resolveBulletPoints(
  structured: string[] | undefined,
  fallbackText: string,
  targetCount = 5,
): string[] {
  if (structured?.length) {
    return structured.slice(0, targetCount).map((line) => line.trim()).filter(Boolean);
  }

  const lines = fallbackText
    .split(/\n+/)
    .map((line) => line.replace(BULLET_PREFIX, "").replace(NUMBERED_PREFIX, "").trim())
    .filter((line) => line.length > 8);

  if (lines.length >= 2) {
    return padBullets(lines, targetCount);
  }

  const sentences = fallbackText
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 12);

  return padBullets(sentences.length ? sentences : [fallbackText], targetCount);
}

function padBullets(items: string[], targetCount: number): string[] {
  if (!items.length) return [];
  const result: string[] = [];
  for (let index = 0; index < targetCount; index += 1) {
    result.push(items[Math.min(index, items.length - 1)]);
  }
  return result;
}
