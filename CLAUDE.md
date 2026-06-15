
## 🗺️ 知识图谱 (Graphify)

本项目已配置 Graphify 知识图谱，可通过以下方式使用：

**在 Claude Code 中使用**：
```
/graphify query "认证如何实现的？"
/graphify explain "UserService"
/graphify path "API" "Database"
```

**查看可视化图谱**：
```bash
open graphify-out/graph.html
```

**查看分析报告**：
```bash
cat graphify-out/GRAPH_REPORT.md
```

**增量更新**（修改代码后）：
```bash
graphify update .
```

详细文档：`_shared/docs/graphify-guide.md`

