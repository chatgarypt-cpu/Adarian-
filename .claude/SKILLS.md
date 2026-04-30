# Adarian 可用 Skills

本目录包含自定义 skills，用于简化重复性操作。

## /test1

运行 test1 种子文件的模拟：

```
cd adarian mvp && uv run python main.py seeds/test1.txt
```

验证输出：
- Phase 1-4 全部完成
- x(t) 序列有数据
- tick_logs 包含 10 轮数据
- final_report.md 生成

## /verify

验证当前代码修改是否正确：

1. 运行模拟命令
2. 检查输出质量指标
3. 报告结果
