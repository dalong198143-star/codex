# Council 实验数据目录

五Agent体系 v3.0-experimental 的所有运行数据。

## 目录结构

```
council/
├── README.md            # 本文件
├── decisions/           # L2+ 决策日志
├── audits/              # 监理报告 + 扣带思核实
├── benchmarks/          # 效率数据（A/B对比结果）
├── daily-summaries/     # 每日总结
└── corrections/         # 规则修正记录
```

## 规则

- 每日至少一次总结，写入 daily-summaries/
- 监理报告、扣带思核实结果存入 audits/
- L2+ 决策存入 decisions/，格式 council-YYYYMMDD-NNN.md
- 每次 A/B 对比结果存入 benchmarks/
- 规则被修改时，原规则 + 修改原因存入 corrections/

## 实验原则

1. 规则是假设，数据是验证
2. 发现规则有问题 → 当天纠正，不等到"下个版本"
3. 监理误报模式存入 corrections/，用于校准
4. 效率比连续3天 > 3x → 触发流程重新设计
