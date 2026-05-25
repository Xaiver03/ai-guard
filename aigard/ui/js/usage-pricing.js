/**
 * AI Guard — 定价配置逻辑
 * 与后端 pricing.py 保持一致
 */

/**
 * 归一化模型名称（与后端 Python 逻辑一致）
 * @param {string} model - 原始模型名
 * @returns {string} 归一化后的模型名
 */
export function normalizeModelName(model) {
  if (!model) return model;

  let name = model.toLowerCase().trim();

  // 去掉前缀
  if (name.startsWith('anthropic/')) {
    name = name.substring('anthropic/'.length);
  }

  // 去掉末尾日期后缀 -YYYYMMDD
  name = name.replace(/-\d{8}$/, '');

  // 去掉末尾日期时间后缀 -YYYYMMDDHHMMSS
  name = name.replace(/-\d{14}$/, '');

  // 去掉修饰词
  name = name.replace(/-(preview|beta|latest|exp|experimental)$/, '');

  return name;
}

/** 内置默认价格（per 1M tokens，USD） */
export const DEFAULT_PRICES = {
  // ===== Claude 4 系列 =====
  'claude-opus-4': { input: 15.0, output: 75.0, cacheWrite: 18.75, cacheRead: 1.5 },
  'claude-sonnet-4': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-sonnet-4-5': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-sonnet-4-6': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-haiku-4-5': { input: 0.8, output: 4.0, cacheWrite: 1.0, cacheRead: 0.08 },

  // ===== Claude 3.7 系列 =====
  'claude-sonnet-3-7': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },

  // ===== Claude 3.5 系列 =====
  'claude-opus-3-5': { input: 15.0, output: 75.0, cacheWrite: 18.75, cacheRead: 1.5 },
  'claude-sonnet-3-5': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-3-5-sonnet': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-haiku-3-5': { input: 0.8, output: 4.0, cacheWrite: 1.0, cacheRead: 0.08 },
  'claude-3-5-haiku': { input: 0.8, output: 4.0, cacheWrite: 1.0, cacheRead: 0.08 },

  // ===== Claude 3 系列 =====
  'claude-opus-3': { input: 15.0, output: 75.0, cacheWrite: 18.75, cacheRead: 1.5 },
  'claude-3-opus': { input: 15.0, output: 75.0, cacheWrite: 18.75, cacheRead: 1.5 },
  'claude-sonnet-3': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-3-sonnet': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-haiku-3': { input: 0.25, output: 1.25, cacheWrite: 0.3, cacheRead: 0.03 },
  'claude-3-haiku': { input: 0.25, output: 1.25, cacheWrite: 0.3, cacheRead: 0.03 },

  // ===== Claude 2 系列 =====
  'claude-2': { input: 8.0, output: 24.0, cacheWrite: 0.0, cacheRead: 0.0 },
  'claude-2-0': { input: 8.0, output: 24.0, cacheWrite: 0.0, cacheRead: 0.0 },
  'claude-2-1': { input: 8.0, output: 24.0, cacheWrite: 0.0, cacheRead: 0.0 },
  'claude-instant-1': { input: 1.63, output: 5.51, cacheWrite: 0.0, cacheRead: 0.0 },
};

// 前缀匹配表（与后端一致）
const PREFIX_FALLBACK = [
  ['claude-opus-4',    'claude-opus-4'],
  ['claude-sonnet-4-6', 'claude-sonnet-4-6'],
  ['claude-sonnet-4-5', 'claude-sonnet-4-5'],
  ['claude-sonnet-4',  'claude-sonnet-4'],
  ['claude-haiku-4-5', 'claude-haiku-4-5'],
  ['claude-haiku-4',   'claude-haiku-4-5'],
  ['claude-sonnet-3-7', 'claude-sonnet-3-7'],
  ['claude-opus-3-5',  'claude-opus-3-5'],
  ['claude-sonnet-3-5', 'claude-sonnet-3-5'],
  ['claude-3-5-sonnet', 'claude-3-5-sonnet'],
  ['claude-haiku-3-5', 'claude-haiku-3-5'],
  ['claude-3-5-haiku', 'claude-3-5-haiku'],
  ['claude-opus-3',    'claude-opus-3'],
  ['claude-3-opus',    'claude-3-opus'],
  ['claude-sonnet-3',  'claude-sonnet-3'],
  ['claude-3-sonnet',  'claude-3-sonnet'],
  ['claude-haiku-3',   'claude-haiku-3'],
  ['claude-3-haiku',   'claude-3-haiku'],
  ['claude-2',         'claude-2'],
  ['claude-instant',   'claude-instant-1'],
  ['claude-',          'claude-sonnet-4-6'],  // 兜底
];

const FALLBACK_PRICING = { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 };

/** 检查模型是否有精确定价 */
export function hasPricing(model) {
  const normalized = normalizeModelName(model);
  return normalized in DEFAULT_PRICES;
}

/** 获取有效价格（精确匹配 > 前缀匹配 > 兜底） */
export function getEffectivePrice(modelKey, allPricing = {}) {
  const normalized = normalizeModelName(modelKey);

  // 从后端传入的完整定价表中查找
  if (allPricing[normalized]) {
    const p = allPricing[normalized];
    return {
      input: p.input_price ?? p.input ?? 0,
      output: p.output_price ?? p.output ?? 0,
      cacheWrite: p.cache_creation_price ?? p.cacheWrite ?? 0,
      cacheRead: p.cache_read_price ?? p.cacheRead ?? 0,
    };
  }
  if (allPricing[modelKey]) {
    const p = allPricing[modelKey];
    return {
      input: p.input_price ?? p.input ?? 0,
      output: p.output_price ?? p.output ?? 0,
      cacheWrite: p.cache_creation_price ?? p.cacheWrite ?? 0,
      cacheRead: p.cache_read_price ?? p.cacheRead ?? 0,
    };
  }

  // 前端本地 fallback（离线时使用）
  if (DEFAULT_PRICES[normalized]) return DEFAULT_PRICES[normalized];

  // 前缀匹配
  for (const [prefix, targetKey] of PREFIX_FALLBACK) {
    if (normalized.startsWith(prefix)) {
      if (DEFAULT_PRICES[targetKey]) return DEFAULT_PRICES[targetKey];
    }
  }

  // 兜底
  return FALLBACK_PRICING;
}

/** 合并检测到的模型与默认价格 */
export function mergeDetectedModels(detectedModels) {
  const models = { ...DEFAULT_PRICES };
  for (const m of detectedModels) {
    const normalized = normalizeModelName(m);
    if (!models[normalized]) {
      // 使用 getEffectivePrice 的匹配逻辑
      models[normalized] = getEffectivePrice(m);
    }
  }
  return models;
}
