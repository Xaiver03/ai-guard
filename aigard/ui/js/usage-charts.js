/**
 * AI Guard — 图表渲染逻辑
 * Chart.js 配置、主题适配、图表创建
 */

/** 从 CSS 变量读取当前主题颜色 */
export function getChartColors() {
  const s = getComputedStyle(document.documentElement);
  const v = (name) => s.getPropertyValue(name).trim();
  return {
    grid: v('--border-default') || v('--border'),
    tick: v('--text-secondary') || v('--muted'),
    tooltipBg: v('--bg-tertiary') || v('--card2'),
    tooltipTitle: v('--text-primary') || v('--text'),
    tooltipBody: v('--text-secondary') || v('--muted'),
    tooltipBorder: v('--border-default') || v('--border'),
    blue: v('--accent-blue') || v('--blue'),
    green: v('--accent-green') || v('--green'),
    orange: v('--accent-yellow') || v('--yellow'),
    purple: v('--accent-purple') || v('--purple'),
    red: v('--accent-red') || v('--red'),
  };
}

/** 构建 Chart.js 通用配置 */
export function buildChartOptions(type, formatCallback) {
  const c = getChartColors();
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: type === 'bar',
        position: 'top',
        labels: {
          color: c.tick,
          font: { size: 11 },
          usePointStyle: true,
          pointStyle: 'rectRounded',
          padding: 16,
        },
      },
      tooltip: {
        backgroundColor: c.tooltipBg,
        titleColor: c.tooltipTitle,
        bodyColor: c.tooltipBody,
        borderColor: c.tooltipBorder,
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        callbacks: formatCallback ? { label: formatCallback } : {},
      },
    },
    scales: {
      x: {
        grid: { color: c.grid + '80', drawBorder: false },
        ticks: { color: c.tick, maxRotation: 0, font: { size: 11 } },
      },
      y: {
        grid: { color: c.grid + '80', drawBorder: false },
        ticks: { color: c.tick, font: { size: 11 } },
      },
    },
  };
}

/** 创建 Token 趋势图（折线图或柱状图） */
export function createTokenChart(ctx, data, isHourly, formatNumber) {
  const c = getChartColors();
  const options = buildChartOptions(isHourly ? 'bar' : 'line', (context) => {
    const label = context.dataset.label || '';
    const value = context.parsed?.y ?? context.parsed;
    return `${label}: ${formatNumber(value)}`;
  });

  options.scales.y.ticks.callback = (value) => formatNumber(value);

  if (isHourly) {
    // 柱状图（堆叠）
    return new Chart(ctx, {
      type: 'bar',
      data: data,
      options: options,
    });
  } else {
    // 折线图
    return new Chart(ctx, {
      type: 'line',
      data: data,
      options: options,
    });
  }
}

/** 创建费用趋势图 */
export function createCostChart(ctx, data, isHourly) {
  const options = buildChartOptions(isHourly ? 'bar' : 'line', (context) => {
    const value = context.parsed?.y ?? context.parsed;
    return `$${value.toFixed(4)}`;
  });

  options.scales.y.ticks.callback = (value) => `$${value.toFixed(2)}`;

  return new Chart(ctx, {
    type: isHourly ? 'bar' : 'line',
    data: data,
    options: options,
  });
}

/** 创建模型分布饼图 */
export function createPieChart(ctx, data, formatNumber) {
  const c = getChartColors();
  return new Chart(ctx, {
    type: 'pie',
    data: data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: c.tooltipBg,
          titleColor: c.tooltipTitle,
          bodyColor: c.tooltipBody,
          borderColor: c.tooltipBorder,
          borderWidth: 1,
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: function (context) {
              const label = context.label || '';
              const value = context.parsed || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = ((value / total) * 100).toFixed(1);
              return `${label}: ${formatNumber(value)} tokens (${percentage}%)`;
            },
          },
        },
      },
    },
  });
}
