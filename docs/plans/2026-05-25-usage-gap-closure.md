# AI Guard Usage 功能差距修复计划

> **目标**：缩小与 vibecafe.ai/usage 的功能差距，提升 Claude 使用统计的准确性和可用性
> 
> **创建时间**：2026-05-25
> 
> **优先级**：P0（基础设施） → P1（核心功能） → P2（增强功能）

---

## 当前差距分析

### 我们有的 ✅
- 词元使用统计（输入/输出/缓存）
- 费用估算
- 模型分布
- 时间维度过滤（今日/周/月/自定义）
- 每日/每小时趋势图
- 定价配置
- 暗色/亮色主题
- 完全本地，无需注册

### 他们有的，我们没有的 ❌
1. **模型名称标准化** — 当前模糊匹配太弱，带日期的模型名无法精确定价
2. **时间范围区分** — 「今天」vs「24H 滚动窗口」
3. **项目维度筛选** — 后端有 API，前端缺 UI
4. **会话级分析** — active time、duration、message count
5. **月视图** — 后端有 API，前端缺 UI
6. **Token 覆盖率（coverage）** — 标注有多少 token 能精确计费

---

## 实施计划

### Phase 0: 基础设施修复（P0）

#### Task #1: 标准化模型名称映射和全量定价表

**问题**：
- 后端 Python 只有 6 个模型，用旧格式（`claude-3-5-sonnet-20241022`）
- 前端 JS 有更多模型，但用简化名（`claude-sonnet-4`）
- JSONL 里实际模型名带日期（`claude-sonnet-4-6-20251101`），无法精确匹配

**解决方案**：
1. **建立模型名称归一化函数**（前后端统一）
   ```python
   # 归一化规则
   claude-sonnet-4-6-20251101 → claude-sonnet-4-6
   claude-3-5-sonnet-20241022 → claude-3-5-sonnet
   anthropic/claude-opus-4-0 → claude-opus-4
   ```

2. **扩充后端定价表**（`aigard/core/usage/pricing.py`）
   - 添加所有 Claude 4.x/3.x 变体
   - 添加其他主流模型（GLM、DeepSeek、Kimi 等）
   - 与前端 JS 定价表保持一致

3. **实现智能匹配逻辑**
   - 精确匹配优先
   - 前缀匹配（去掉日期后缀）
   - 兜底到 Sonnet 4.6 价格

**涉及文件**：
- `aigard/core/usage/pricing.py` — 扩充 DEFAULT_PRICING，添加 normalize_model_name()
- `aigard/core/usage/calculator.py` — 使用归一化后的模型名
- `aigard/ui/js/usage-pricing.js` — 同步定价数据

**验收标准**：
- [ ] 所有 Claude 4.x/3.x 模型都有精确定价
- [ ] 带日期的模型名能正确归一化
- [ ] 前后端定价数据一致
- [ ] 未知模型有合理兜底价格

---

### Phase 1: 核心功能补齐（P1）

#### Task #2: 实现 Token 覆盖率（coverage）指标

**功能**：
- 计算有定价的 token 占比
- 标记未识别模型
- 在 UI 显示覆盖率百分比

**实现步骤**：
1. **后端计算逻辑**（`aigard/core/usage/calculator.py`）
   ```python
   def calculate_coverage(self, entries: List[UsageEntry]) -> dict:
       total_tokens = 0
       priced_tokens = 0
       unknown_models = set()
       
       for entry in entries:
           tokens = entry.input_tokens + entry.output_tokens + ...
           total_tokens += tokens
           
           # 检查是否有定价
           if self.pricing_manager.has_pricing(entry.model):
               priced_tokens += tokens
           else:
               unknown_models.add(entry.model)
       
       coverage = (priced_tokens / total_tokens * 100) if total_tokens > 0 else 100
       return {
           'coverage_percent': coverage,
           'total_tokens': total_tokens,
           'priced_tokens': priced_tokens,
           'unknown_models': list(unknown_models)
       }
   ```

2. **API 端点**（`aigard/api/usage.py`）
   - 在 `/api/usage/summary` 响应中添加 `coverage` 字段

3. **前端展示**（`aigard/ui/usage.html`）
   - 在主要统计卡片区添加覆盖率卡片
   - 显示百分比 + 进度条
   - 鼠标悬停显示未识别模型列表

**涉及文件**：
- `aigard/core/usage/calculator.py` — 添加 calculate_coverage()
- `aigard/core/usage/pricing.py` — 添加 has_pricing()
- `aigard/api/usage.py` — 修改 /api/usage/summary
- `aigard/ui/usage.html` — 添加覆盖率卡片
- `aigard/ui/js/usage-data.js` — 处理 coverage 数据

**验收标准**：
- [ ] 覆盖率计算准确（有定价 token / 总 token）
- [ ] UI 显示覆盖率百分比和进度条
- [ ] 能查看未识别模型列表
- [ ] 覆盖率 < 100% 时有视觉提示

---

#### Task #3: 拆分「今天」vs「24H」时间范围按钮

**功能**：
- **今天** = 本地零点到现在（起点固定，只增不减）
- **24H** = 最近滚动 24 小时（原 `today` 行为）

**实现步骤**：
1. **后端 API 修改**（`aigard/api/usage.py`）
   ```python
   def _resolve_date_range(start_date, end_date, preset):
       now = datetime.now()
       today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
       
       if preset == 'today':
           # 今天：本地零点到现在
           return today_start.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')
       elif preset == '24h':
           # 24H：滚动窗口
           start = (now - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
           return start, now.strftime('%Y-%m-%d %H:%M:%S')
       # ... 其他 preset
   ```

2. **前端按钮修改**（`aigard/ui/usage.html`）
   ```html
   <button data-range="today">今日</button>
   <button data-range="24h">24H</button>
   <button data-range="yesterday">昨天</button>
   ```

3. **图表标题动态调整**
   - 「今天」模式：显示「今日词元使用趋势」
   - 「24H」模式：显示「最近 24 小时词元使用趋势」

**涉及文件**：
- `aigard/api/usage.py` — 修改 _resolve_date_range()
- `aigard/ui/usage.html` — 修改时间范围按钮
- `aigard/ui/js/usage-data.js` — 添加 24h 处理逻辑
- `aigard/ui/js/usage-i18n.js` — 添加翻译

**验收标准**：
- [ ] 「今天」按钮：零点到现在，数字只增不减
- [ ] 「24H」按钮：滚动窗口，最早的小时会滑出
- [ ] 图表标题根据模式动态调整
- [ ] 两种模式都按小时聚合

---

#### Task #4: 添加月视图 Tab

**功能**：
- 后端已有 `/api/usage/monthly`
- 前端添加月视图展示

**实现步骤**：
1. **前端 Tab 切换**（`aigard/ui/usage.html`）
   ```html
   <div class="view-tabs">
     <button class="active" data-view="daily">日视图</button>
     <button data-view="hourly">时视图</button>
     <button data-view="monthly">月视图</button>
   </div>
   ```

2. **月度图表**（`aigard/ui/js/usage-charts.js`）
   - 创建 createMonthlyChart() 函数
   - X 轴：月份（2026-01, 2026-02...）
   - Y 轴：总 token 数 / 费用

3. **月度统计表**
   - 显示每月的 token 数、费用、使用模型数
   - 可点击展开查看该月的每日数据

**涉及文件**：
- `aigard/ui/usage.html` — 添加月视图 Tab 和容器
- `aigard/ui/js/usage-data.js` — 添加 loadMonthlyData()
- `aigard/ui/js/usage-charts.js` — 添加 createMonthlyChart()
- `aigard/ui/js/usage-i18n.js` — 添加翻译

**验收标准**：
- [ ] 月视图 Tab 可切换
- [ ] 月度趋势图正确显示
- [ ] 月度统计表包含所有关键指标
- [ ] 可展开查看月内每日数据

---

#### Task #5: 实现项目维度筛选

**功能**：
- 后端已有 `/api/usage/projects`
- 前端添加项目下拉筛选器

**实现步骤**：
1. **前端筛选器 UI**（`aigard/ui/usage.html`）
   ```html
   <div class="filter-bar">
     <label>项目:</label>
     <select id="project-filter">
       <option value="">全部项目</option>
       <!-- 动态加载 -->
     </select>
   </div>
   ```

2. **加载项目列表**（`aigard/ui/js/usage-data.js`）
   ```javascript
   async function loadProjects() {
     const res = await fetch('/api/usage/projects');
     const data = await res.json();
     return data.projects;
   }
   ```

3. **筛选逻辑**
   - 选择项目后，所有 API 请求添加 `?project=xxx` 参数
   - 后端 API 支持 project 参数过滤

**涉及文件**：
- `aigard/api/usage.py` — 添加 project 参数支持
- `aigard/core/usage/loader.py` — 已有 load_project_usage()
- `aigard/ui/usage.html` — 添加项目筛选器
- `aigard/ui/js/usage-data.js` — 添加项目筛选逻辑

**验收标准**：
- [ ] 项目下拉列表正确加载
- [ ] 选择项目后数据正确过滤
- [ ] 「全部项目」选项恢复全量数据
- [ ] 项目筛选与时间范围筛选可组合

---

### Phase 2: 增强功能（P2）

#### Task #6: 添加会话级分析

**功能**：
- 提取每个 session 的元数据
- 显示会话列表和详情

**实现步骤**：
1. **扩展数据模型**（`aigard/core/usage/models.py`）
   ```python
   @dataclass(slots=True)
   class SessionSummary:
       session_id: str
       project: str
       start_time: datetime
       end_time: datetime
       duration_seconds: int
       active_seconds: int  # AI 生成时间
       message_count: int
       total_tokens: int
       total_cost: float
       models_used: List[str]
   ```

2. **会话数据提取**（`aigard/core/usage/loader.py`）
   ```python
   def load_session_summaries(self) -> List[SessionSummary]:
       # 按 session_id 分组
       # 计算每个 session 的时间跨度、消息数等
   ```

3. **API 端点**（`aigard/api/usage.py`）
   ```python
   @router.get("/sessions")
   async def get_sessions(
       start_date: Optional[str] = None,
       end_date: Optional[str] = None,
       project: Optional[str] = None
   ):
       # 返回会话列表
   ```

4. **前端会话视图**（`aigard/ui/usage.html`）
   - 添加「会话」Tab
   - 显示会话列表表格
   - 点击会话查看详情（时间线、token 分布）

**涉及文件**：
- `aigard/core/usage/models.py` — 添加 SessionSummary
- `aigard/core/usage/loader.py` — 添加 load_session_summaries()
- `aigard/api/usage.py` — 添加 /api/usage/sessions
- `aigard/ui/usage.html` — 添加会话视图
- `aigard/ui/js/usage-data.js` — 添加会话数据处理

**验收标准**：
- [ ] 会话列表显示所有关键指标
- [ ] 可按项目/时间筛选会话
- [ ] 点击会话查看详情
- [ ] 显示 active time vs total duration

---

## 实施顺序

```
Phase 0 (基础设施)
├─ Task #1: 模型名称标准化 ⚠️ 必须先做，影响所有后续功能
│
Phase 1 (核心功能)
├─ Task #2: Token 覆盖率 ← 依赖 Task #1
├─ Task #3: 今天 vs 24H ← 独立
├─ Task #4: 月视图 ← 独立
└─ Task #5: 项目筛选 ← 独立
│
Phase 2 (增强功能)
└─ Task #6: 会话分析 ← 依赖 Task #1
```

**建议执行顺序**：
1. Task #1（模型名称标准化）— 基础设施，必须先做
2. Task #2（Token 覆盖率）— 依赖 #1，提升准确性
3. Task #3（今天 vs 24H）— 快速见效，用户体验提升
4. Task #5（项目筛选）— 快速见效，后端已有 API
5. Task #4（月视图）— 快速见效，后端已有 API
6. Task #6（会话分析）— 复杂度高，最后做

---

## 技术债务清理

### 1. 前后端定价数据不一致
- **问题**：Python 用旧格式，JS 用简化名
- **解决**：Task #1 统一

### 2. 模糊匹配逻辑太弱
- **问题**：带日期的模型名无法匹配
- **解决**：Task #1 归一化

### 3. 缺少模型识别率指标
- **问题**：不知道有多少 token 无法定价
- **解决**：Task #2 覆盖率

### 4. 时间范围语义不清
- **问题**：「今日」是零点还是 24 小时？
- **解决**：Task #3 拆分按钮

---

## 测试策略

### 单元测试
- [ ] 模型名称归一化函数
- [ ] 定价匹配逻辑
- [ ] 覆盖率计算
- [ ] 时间范围解析

### 集成测试
- [ ] 完整数据流：JSONL → 解析 → 聚合 → API → 前端
- [ ] 项目筛选 + 时间范围组合
- [ ] 多模型混合场景

### 手动测试
- [ ] 使用真实 ~/.claude 数据测试
- [ ] 验证费用估算准确性
- [ ] 检查 UI 响应性能

---

## 性能优化

### 当前性能
- 首次加载：~10 秒（解析 16.5 万条记录）
- 后续请求：毫秒级（SQLite 缓存）

### 优化方向
1. **增量解析**：只解析新增的 JSONL 文件
2. **并行解析**：多进程处理多个项目
3. **索引优化**：SQLite 添加复合索引
4. **前端缓存**：localStorage 缓存项目列表

---

## 文档更新

完成后需要更新：
- [ ] `README.md` — 添加新功能说明
- [ ] `CLAUDE.md` — 更新技术栈和架构
- [ ] `docs/api.md` — 更新 API 文档（如果有）
- [ ] 前端 UI 添加功能说明 tooltip

---

## 里程碑

- **M1 (Week 1)**：Task #1 完成，定价准确性提升
- **M2 (Week 2)**：Task #2-3 完成，核心功能补齐
- **M3 (Week 3)**：Task #4-5 完成，功能对齐 vibecafe
- **M4 (Week 4)**：Task #6 完成，超越 vibecafe（本地 + 会话分析）

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 模型名称变体太多 | 归一化失败 | 建立测试用例库，覆盖所有已知变体 |
| 定价数据过时 | 费用估算不准 | 定期从官网同步，支持用户手动覆盖 |
| 会话数据提取复杂 | 开发延期 | 先做简单版本，后续迭代 |
| 性能下降 | 用户体验差 | 增量解析 + 缓存优化 |

---

## 参考资料

- [vibecafe.ai/usage](https://vibecafe.ai/usage) — 竞品功能
- [vibe-usage GitHub](https://github.com/vibe-cafe/vibe-usage) — 开源 CLI 工具
- [Claude API Pricing](https://www.anthropic.com/pricing) — 官方定价
- [ccusage](https://github.com/rocalight/ccusage) — 原始项目（已融合）
