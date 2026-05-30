/**
 * AI Guard — Claude 使用统计数据处理
 * 移植自 ccusage App.jsx 的数据逻辑
 */

/** 从 API 并行加载数据 */
export async function loadAllData(preset, project = null, source = null) {
  const params = new URLSearchParams();
  if (preset) params.append('preset', preset);
  if (project) params.append('project', project);
  if (source) params.append('source', source);
  const queryString = params.toString() ? `?${params.toString()}` : '';

  const [summary, daily, models] = await Promise.all([
    fetch(`/api/usage/summary${queryString}`).then(r => r.json()),
    fetch(`/api/usage/daily${queryString}`).then(r => r.json()),
    fetch(`/api/usage/models${queryString}`).then(r => r.json()),
  ]);
  return { summary, daily, models };
}

/** 从 API 加载小时数据 */
export async function loadHourlyData(preset, project = null, source = null) {
  const params = new URLSearchParams();
  if (preset) params.append('preset', preset);
  if (project) params.append('project', project);
  if (source) params.append('source', source);
  const queryString = params.toString() ? `?${params.toString()}` : '';
  return fetch(`/api/usage/hourly${queryString}`).then(r => r.json());
}

/** 判断是否为小时级视图 */
export function isHourlyRange(range) {
  return range === 'today' || range === '24h' || range === 'yesterday' || range === 'last_3_days';
}

/** 按时间范围过滤日数据 */
export function filterDailyByRange(dailyData, range, startDate, endDate) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  switch (range) {
    case 'today':
      return dailyData.filter(d => new Date(d.date) >= today);
    case 'yesterday': {
      const y = new Date(today); y.setDate(y.getDate() - 1);
      return dailyData.filter(d => { const dd = new Date(d.date); return dd >= y && dd < today; });
    }
    case 'last_3_days': {
      const s = new Date(today); s.setDate(s.getDate() - 3);
      return dailyData.filter(d => new Date(d.date) >= s);
    }
    case 'this_week': {
      const s = new Date(today); s.setDate(s.getDate() - 7);
      return dailyData.filter(d => new Date(d.date) >= s);
    }
    case 'this_month': {
      const s = new Date(today); s.setDate(s.getDate() - 30);
      return dailyData.filter(d => new Date(d.date) >= s);
    }
    case 'custom': {
      if (!startDate || !endDate) return dailyData;
      const s = new Date(startDate);
      const e = new Date(endDate); e.setDate(e.getDate() + 1);
      return dailyData.filter(d => { const dd = new Date(d.date); return dd >= s && dd < e; });
    }
    default:
      return dailyData;
  }
}

/** 构建完整小时槽位（填充缺失小时） */
export function buildHourlyBuckets(rawHourly, forceDate = null) {
  // 如果指定了日期（如今天），只创建该日期的 24 个桶
  // 否则根据数据中出现的日期创建桶
  let datesToUse;
  if (forceDate) {
    datesToUse = [forceDate];
  } else {
    const dates = new Set();
    for (const item of rawHourly) {
      if (item.hour && item.hour.length >= 10) dates.add(item.hour.substring(0, 10));
    }
    const sortedDates = Array.from(dates).sort();
    datesToUse = sortedDates.length > 0 ? sortedDates : [new Date().toLocaleDateString('en-CA')];
  }

  const buckets = {};
  const emptyBucket = () => ({
    inputTokens: 0, outputTokens: 0, cacheCreationTokens: 0, cacheReadTokens: 0,
    totalTokens: 0, totalCost: 0, modelsUsed: [], modelBreakdowns: [],
  });

  for (const dateStr of datesToUse) {
    for (let h = 0; h < 24; h++) {
      const key = `${dateStr}T${String(h).padStart(2, '0')}`;
      buckets[key] = { hour: key, ...emptyBucket() };
    }
  }

  for (const item of rawHourly) {
    if (buckets[item.hour]) {
      buckets[item.hour] = {
        hour: item.hour,
        inputTokens: item.input_tokens || 0,
        outputTokens: item.output_tokens || 0,
        cacheCreationTokens: item.cache_creation_tokens || 0,
        cacheReadTokens: item.cache_read_tokens || 0,
        totalTokens: item.total_tokens || 0,
        totalCost: item.total_cost || 0,
        modelsUsed: item.models_used || [],
        modelBreakdowns: item.model_breakdowns || [],
      };
    }
  }

  return Object.values(buckets).sort((a, b) => a.hour.localeCompare(b.hour));
}

/** 聚合模型统计 */
export function aggregateModelStats(sourceData) {
  const stats = {};
  for (const item of sourceData) {
    const breakdowns = item.model_breakdowns || item.modelBreakdowns;
    if (!breakdowns) continue;
    for (const bd of breakdowns) {
      const name = bd.model_name || bd.modelName;
      if (!name) continue;
      const short = shortenModelName(name);
      if (!stats[short]) {
        stats[short] = { tokens: 0, cost: 0, fullName: name, input: 0, output: 0, cacheWrite: 0, cacheRead: 0, requestCount: 0 };
      }
      const s = stats[short];
      const inp = bd.input_tokens || bd.inputTokens || 0;
      const out = bd.output_tokens || bd.outputTokens || 0;
      const cw = bd.cache_creation_tokens || bd.cacheCreationTokens || 0;
      const cr = bd.cache_read_tokens || bd.cacheReadTokens || 0;
      s.tokens += inp + out + cw + cr;
      s.cost += bd.cost || 0;
      s.input += inp;
      s.output += out;
      s.cacheWrite += cw;
      s.cacheRead += cr;
      s.requestCount += bd.request_count || bd.requestCount || 0;
    }
  }
  return Object.entries(stats).sort((a, b) => b[1].tokens - a[1].tokens);
}

/** 计算汇总指标 */
export function calculateTotals(sourceData) {
  let totalTokens = 0, totalCost = 0, totalInput = 0, totalOutput = 0;
  let totalCacheWrite = 0, totalCacheRead = 0, totalRequests = 0;
  for (const item of sourceData) {
    totalTokens += item.total_tokens || item.totalTokens || 0;
    totalCost += item.total_cost || item.totalCost || 0;
    totalInput += item.input_tokens || item.inputTokens || 0;
    totalOutput += item.output_tokens || item.outputTokens || 0;
    totalCacheWrite += item.cache_creation_tokens || item.cacheCreationTokens || 0;
    totalCacheRead += item.cache_read_tokens || item.cacheReadTokens || 0;
    if (item.model_breakdowns || item.modelBreakdowns) {
      const bds = item.model_breakdowns || item.modelBreakdowns || [];
      totalRequests += bds.reduce((s, b) => s + (b.request_count || b.requestCount || 0), 0);
    }
  }
  return { totalTokens, totalCost, totalInput, totalOutput, totalCacheWrite, totalCacheRead, totalRequests };
}

/** 格式化数字 */
export function formatNumber(num, mode = 'compact') {
  if (num == null) return '0';
  if (mode === 'full') return Math.round(num).toLocaleString('en-US');
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(2) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
}

/** 简化模型名称 */
export function shortenModelName(name) {
  return name.replace('anthropic/', '').replace('claude-', '').replace(/-\d{8}$/, '');
}

/** 16 色调色板 */
export const MODEL_COLORS = [
  '#58a6ff', '#3fb950', '#d29922', '#f85149', '#bc8cff',
  '#79c0ff', '#56d364', '#e3b341', '#ff7b72', '#d2a8ff',
  '#a5d6ff', '#7ee787', '#ffd33d', '#ffa198', '#d2a8ff', '#80ccff',
];
