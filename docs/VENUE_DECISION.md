# 投稿期刊评估：JSS 还是 SPE

> 评估时点：2026-09-24。依据：本项目已完成的研究内容，
> 加上对 JSS（826 篇）与 SPE（241 篇）近两年发文的定向统计（`research/venue_fit_scan.py`）。

---

## 一、结论

**投 JSS 常规通道，投之前先补两件事。**

理由是**范围匹配**，而不是影响因子或难度：

SPE 的官方 Aims and Scope 列出的主题是分布式计算范式、领域计算、模型驱动开发、
网络、操作系统与运行时、程序语言与编译器、复用。它的关键词表是
*software implementation, software tools, compilers, run-time systems,
systems programming, debugging, programming techniques, algorithms*。

**这份清单里没有一个能容纳"某个应用层工具生态的实证普查"。**
本项目不研究运行时、不研究编译器、不研究系统编程，也不提出算法或工具。
它研究的是软件制品（清单、schema、凭据声明、版本历史）的属性。

SPE 的失败模式恰恰是范围不符被主编直接拒稿——其作者指南原文写明
"a large fraction of new submissions are rejected without being refereed
because the editors consider the topics covered by the submission to be
outside the journal's scope"。用一篇范围擦边的稿子去撞这条，是最不划算的赌法。

---

## 二、统计依据

在两刊近两年语料中检索与本项目同形态的研究：

| 研究形态 | JSS | SPE | 倍数 |
| --- | --- | --- | --- |
| 生态 / 制品挖掘 | **71** | 23 | 3.1× |
| 包 / 注册表 / 市场分析 | **12** | 4 | 3.0× |
| 分类学 / 刻画型贡献 | **64** | 28 | 2.3× |
| 安全态势分析 | 6 | **10** | 0.6× |
| 接口 / API 设计质量 | **21** | 2 | 10.5× |
| 智能体 / 工具生态 | **3** | 0 | — |

两点必须说明：

1. **SPE 那 4 篇"包/注册表"命中全是假阳性**（数据湖、分布式训练、
   缺陷预测、无服务器工作流），没有一篇真的是包生态研究。
2. SPE 在"安全态势"上确实多（10 对 6），但全部是云、联邦学习、
   区块链方向的安全，不是软件制品层面的凭据与权限分析。

### 直接可对标的先例，全在 JSS

| 论文 | 年 | 与本项目的关系 |
| --- | --- | --- |
| *Agent design pattern catalogue* | 2025，被引 48 | JSS 近两年被引最高之一，主题就是基础模型智能体的架构模式 |
| *Detecting and removing bloated dependencies in CommonJS packages* | 2025 | 包生态的制品级实证 |
| *Many hands make light work: An LLM-based multi-agent system for detecting malicious PyPI packages* | 2026 | PyPI 生态 + 供应链安全 |
| *On the adoption of software bill of materials in open-source software projects* | 2025 | 供应链元数据的采用实证 |
| *Technical debt in AI-enabled systems* | 2024，被引 31 | AI 使能系统的实证研究 |

SPE 侧最接近的是 *Large-scale characterization of Java streams*（2023，30 页）
和 *Is There a Correlation Between Readme Content and Project Meta-Characteristics?*
（2024）——存在，但孤立，不构成一条线。

---

## 三、JSS 官方口味的逐条对齐

JSS 官方主题列表中直接对口的四条：

| JSS 官方主题 | 本项目的对应 |
| --- | --- |
| Software Engineering for AI systems | 智能体工具层的工程属性（RQ1、RQ2） |
| Methods and tools for empirical software engineering research | 抽取管线的构建与验证（RQ4，99.7% 召回） |
| Artificial Intelligence, data analytics and big data applied in software engineering | 6.5 万条制品记录、12,065 个工具定义的大规模分析 |
| Metrics and evaluation of software development resources | 生态增长、版本流失集中度、可审计性指标 |

JSS 明确欢迎的三类稿件，本项目命中两类：

- **reports of practical experience** —— 完整的生态普查与可复现管线
- **studies with negative results** —— 我们有三个真负面结果：
  零明文/裸 IP/localhost 端点（是注册表校验的产物而非发布者自律）、
  63% 服务器只发一版即废弃、
  以及"何时使用"这一字段两位编码者只能达到 fair 一致

**"与具体应用领域无关的贡献"** 这条 JSS 硬要求也有对应：
RQ4 回答的是"一个智能体工具生态有多少比例能仅凭机器可读制品被审计"，
这是可迁移到任何插件/扩展/市场生态的结论，不依赖 MCP 本身。

---

## 四、SPE 特刊那条路为什么不是优选

SPE 现有开放特刊 **AI-Native Software Engineering**（截止 2027-01-15），
主题里确实包含"多智能体软件工程与智能体编排"、"可信、安全、隐私与负责任 AI 采用"、
"度量、基准与评估"。表面上像是对口。

但通读征稿全文，它的核心问题是**人机协作**：

> "how humans and AI agents coordinate, collaborate, and jointly contribute
> to software engineering"
> "AI systems are becoming integral members of software development teams,
> participating in requirements elicitation, software design, implementation..."

本项目不研究协作，不研究智能体在软件生命周期中的行为，也不运行任何模型。
它研究的是智能体所调用的工具那一层的制品属性。这是**相邻**，不是**核心**。

特刊的客座编辑对范围擦边稿的处理通常比常规通道更严格，因为特刊本身要维护主题一致性。
所以走特刊并不是"命中率更高的捷径"，而是一次范围赌注。

**结论**：不投 SPE 特刊。若一定要用 SPE，只能投常规通道，
且必须把贡献重构成"面向智能体工具生态的已验证审计方法"，把抽取管线当主贡献——
但即使重构成功，SPE 的范围清单里依然没有这个主题的位置。

---

## 五、投 JSS 之前必须先补的两件事

### 1. 修掉编码信度上的四个弱字段（约 2 小时人工）

这是**唯一可能让 JSS 审稿人直接拒稿的地方**。JSS 对编码类实证研究几乎必然会
要求报告信度，而目前：

| 字段 | κ | 状态 |
| --- | --- | --- |
| desc_states_when_to_use | 0.233 | 头条结论所在字段，只能报区间 |
| secret_documented_as_secret | 0.229 | 仅可作参考 |
| desc_names_side_effects | 0.149 | 手册枚举缺陷，需 v1.2 |
| readme_warns_about_risk | 不可估 | 两人均无法判定，建议弃用 |

两条路径，任选：

- **A（推荐）**：写 v1.2 手册修掉 `desc_names_side_effects` 的枚举问题，
  两位编码者对 50 项重编一轮。成本约 2 小时，换掉全部四个弱字段。
- **B**：不重编，在论文里把这些字段降级为"指示性"，
  `when_to_use` 报 4%–24% 区间并把分歧本身作为发现。

路径 B 也是诚实的，但 JSS 审稿人有较大概率要求补做，反而拖长周期。
建议走 A。

### 2. 补 GitHub 仓库富集（全自动，你只需配 token）

JSS 的 threats to validity 章节会被逐条审。目前最大的效度威胁是
**T1：注册表时间戳不等于作者发布意图**——注册表版本数中位间隔 0.5 天，
这是批量发布的产物。

补跑 `scripts/05_enrich_github.py --releases` 后，就能用"GitHub 打过的
release 数"与"注册表版本数"做对照，把 T1 从"已声明"变成"已检验"。
这一步对你的时间成本为零，对审稿印象的边际收益很高。

---

## 六、投哪一条通道

| 通道 | 判断 | 理由 |
| --- | --- | --- |
| **JSS 常规研究论文** | **选这个** | 范围最匹配；本项目是完整验证过的实证研究 |
| JSS「SE for Trustworthy Systems」特刊（截止 2026-12-10） | 备选 | 主题是可信智能*系统*，本项目是工具层制品的可信属性，属部分匹配；且与 SEAA 2026 会议挂钩，优先考虑会议扩展稿 |
| JSS In Practice | 不适用 | 该通道面向工业实践经验报告；本项目是研究型普查 |
| JSS New Ideas and Trends | 不适用 | 该通道面向尚未完整验证的新想法；本项目已完成验证 |
| SPE 常规通道 | 不推荐 | 范围清单无对应位置 |
| SPE AI-Native SE 特刊 | 不推荐 | 核心议题是人机协作，本项目不涉及 |

**JSS Open Science 声明：勾选参与。** 零成本、不影响录用结果，
且我们的复现包（管线 + 抽样记录 + 逐文件 SHA-256）已经就位，
正好满足其材料可用性审查。

---

## 七、下一步

1. 决定走第 5.1 节的路径 A 还是 B
2. 配好新 token，跑 GitHub 富集
3. 我按 JSS 的硬要求产出稿件骨架：RQ1–RQ4、证据映射表、
   四分类 threats to validity、Highlights（3–5 条，每条 ≤85 字符）、
   图形摘要，以及 Data availability 声明

你此前那篇 JSS 稿件的格式自检脚本与模板可直接复用，不需要重新踩一遍格式坑。
