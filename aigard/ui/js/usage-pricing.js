/**
 * AI Guard — 定价配置逻辑
 * 从 ccusage PricingConfig.jsx 移植
 */

const STORAGE_KEY = 'ccusage_pricing_overrides';

/** 内置默认价格（per 1M tokens，USD） */
export const DEFAULT_PRICES = {
  // Claude 4 系列
  'claude-opus-4': { input: 15.0, output: 75.0, cacheWrite: 18.75, cacheRead: 1.5 },
  'claude-sonnet-4': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-sonnet-4-5': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-sonnet-4-6': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-haiku-4-5': { input: 1.0, output: 5.0, cacheWrite: 1.25, cacheRead: 0.1 },
  // Claude 3.x 系列
  'claude-opus-3-5': { input: 15.0, output: 75.0, cacheWrite: 18.75, cacheRead: 1.5 },
  'claude-sonnet-3-5': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-haiku-3-5': { input: 0.8, output: 4.0, cacheWrite: 1.0, cacheRead: 0.08 },
  'claude-opus-3': { input: 15.0, output: 75.0, cacheWrite: 18.75, cacheRead: 1.5 },
  'claude-sonnet-3': { input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3 },
  'claude-haiku-3': { input: 0.25, output: 1.25, cacheWrite: 0.3, cacheRead: 0.03 },
  // GLM 系列
  'glm-4.5': { input: 0.6, output: 2.2, cacheWrite: 0.0, cacheRead: 0.0 },
  'glm-4.5-air': { input: 0.13, output: 0.85, cacheWrite: 0.0, cacheRead: 0.0 },
  'glm-5-turbo': { input: 1.2, output: 4.0, cacheWrite: 0.0, cacheRead: 0.0 },
  'glm-5.1': { input: 1.26, output: 3.96, cacheWrite: 0.0, cacheRead: 0.0 },
  // DeepSeek 系列
  'deepseek-v4-pro': { input: 0.145, output: 3.48, cacheWrite: 0.0, cacheRead: 0.0 },
  'deepseek-v4-flash': { input: 0.135, output: 0.28, cacheWrite: 0.0, cacheRead: 0.0 },
  // MiniMax 系列
  'MiniMax-M2.7-highspeed': { input: 0.3, output: 1.2, cacheWrite: 0.0, cacheRead: 0.0 },
  // Kimi 系列
  'kimi-for-coding': { input: 0.6, output: 3.0, cacheWrite: 0.0, cacheRead: 0.0 },
  // MiMo 系列
  'mimo-v2.5-pro': { input: 1.0, output: 3.0, cacheWrite: 0.0, cacheRead: 0.0 },
};

/** 从 localStorage 加载用户覆盖 */
export function loadPricingOverrides() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

/** 保存用户覆盖到 localStorage */
export function savePricingOverrides(overrides) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides));
}

/** 获取有效价格（用户覆盖 > 默认价格 > 兜底） */
export function getEffectivePrice(modelKey, overrides = {}) {
  return overrides[modelKey] || DEFAULT_PRICES[modelKey] || {
    input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3
  };
}

/** 合并检测到的模型与默认价格 */
export function mergeDetectedModels(detectedModels) {
  const models = { ...DEFAULT_PRICES };
  for (const m of detectedModels) {
    if (!models[m]) {
      // 尝试前缀匹配
      const matchKey = Object.keys(models).find(k => m.includes(k) || k.includes(m));
      models[m] = matchKey ? { ...models[matchKey] } : {
        input: 3.0, output: 15.0, cacheWrite: 3.75, cacheRead: 0.3
      };
    }
  }
  return models;
}
