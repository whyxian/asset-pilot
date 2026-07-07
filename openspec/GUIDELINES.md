### 📋 《OpenSpec 使用标准》参考模版

#### 1. 目标与原则

*   **目标**：在“过度设计”和“毫无规划”之间找到平衡。OpenSpec 是用来管理**有意义的、需要记录的变更**，而不是所有代码改动。
*   **核心原则**：**大规划用 OpenSpec，小改动直接改。** 判断依据是“这个变更是否值得在未来被追溯和讨论”。

#### 2. 触发条件（什么时候必须使用）

满足以下 **任意一条** 的变更，**必须**创建 OpenSpec 变更提案，否则代码评审不予通过：

1.  **新功能开发**：任何对用户可见的新特性（例如：添加“导出PDF”功能）。
2.  **架构性变更**：涉及技术选型、模块间接口定义、数据库迁移方案等。
3.  **破坏性变更**：会改变现有 API 行为、数据格式或用户界面交互方式的修改。
4.  **预计耗时 > 1天**：如果预估编码实现时间超过 1 个工作日。
5.  **涉及时长变更**：任何需要更新 `openspec/specs/` 中现有规范的变更。

#### 3. 豁免条件（什么时候不用管）

以下情况可以**跳过** OpenSpec 流程，直接提交代码或修复：

1.  **明显的 Bug 修复**：例如修正空指针、改正错别字、修复样式错位。
2.  **低风险配置**：环境变量、依赖版本升级（非重大版本）、日志级别调整。
3.  **代码内务**：变量/函数重命名、注释修正、代码格式调整（Lint/Fix）、`.gitignore` 修改。
4.  **个人实验性分支**：未经评审的 POC（概念验证）分支，用完即删。

**追加说明**：豁免并不意味着不需要代码评审，只是跳过了规划阶段。

#### 3a. 微变更通道（介于豁免与完整流程之间）

对于**简单的、不影响 spec 的变更**（如调整文档、修改单文件逻辑、加一个工具函数），可以用 **仅 proposal + tasks** 的简化流程，跳过 design 和 specs：

- 执行 `/opsx:propose` 时在 proposal 中注明 `（微变更，跳过 design/specs）`
- 评审只审 proposal 和 tasks
- `/opsx:apply` 时自动忽略缺失的 artifacts

判断标准：**"不用写 design 别人也能理解这是怎么改的"** 就算微变更。如果有技术选型争论或跨模块影响，就走完整流程。

#### 4. 变更粒度标准（一个提案多大合适？）

*   **单一职责**：一个变更只解决一个问题或实现一个功能点。
*   **可独立回滚**：一个变更的代码应该可以在不破坏其他功能的前提下被撤销。
*   **单个 PR 可容纳**：理想情况下，一个 OpenSpec 提案产生的代码变动，应该能在一个 Pull Request 中完成评审。
*   **拆分的信号**：如果你的 `tasks.md` 列表超过了 15 项，或者涉及 3 个以上不相关的模块，建议拆分为多个更小的变更。

#### 5. 标准工作流

所有采用 OpenSpec 的变更，统一遵循以下步骤：

| 阶段 | 负责人 | 操作 |
| :--- | :--- | :--- |
| **探索** (可选) | 开发者 | 如需求模糊，用 `/opsx:explore` 与 AI 讨论，明确范围。 |
| **提案** | 开发者 | 执行 `/opsx:propose` 生成 `proposal.md`、`design.md`、`tasks.md`。 |
| **评审** | 开发者/团队 | 在 IDE 中审阅生成的 Markdown 文件，**确认无误再写代码**。 |
| **实施** | 开发者 | 执行 `/opsx:apply`，按任务清单逐项实现。 |
| **验证** | 开发者 | 完成测试，确保功能符合 `proposal.md` 的描述。 |
| **归档** | 开发者 | 实施完成后执行 `/opsx:archive <变更名>`。OpenSpec 归档与代码合并是独立操作——代码可先提交，归档可以后做。归档前检查是否有 delta spec 需要同步（见 §5a）。 |

#### 5a. 归档前检查：Spec 同步

change 的 `specs/` 目录描述了这个 change 引入的"能力需求"。归档时需要按以下规则回写到主目录 `openspec/specs/`：

| change 的 specs 情况 | 对应主目录 | 操作 | 方法 |
|---|---|---|---|
| **新能力**（change 有 specs，主目录无对应目录） | 不存在 | **copy** | 手动将 change 的 `specs/<能力>/spec.md` 复制到 `openspec/specs/<能力>/spec.md`，去掉 `## ADDED Requirements` header |
| **修改现有能力**（change 有 MODIFIED 内容，主目录已有对应目录） | 已存在 | **delta merge** | 执行 `/opsx:sync <变更名>`，将 delta spec 合并到主 spec |
| **无 spec 变更**（change 无 specs 或 specs 为空） | — | **跳过** | 直接归档 |

**新能力 copy 示例：**

```bash
# change 中的 specs 结构
openspec/changes/archive/YYYY-MM-DD-xxx/specs/closed-holding-dietz-return/spec.md

# 复制到主目录
mkdir -p openspec/specs/closed-holding-dietz-return
cp path/to/change/spec.md openspec/specs/closed-holding-dietz-return/
# 然后编辑去掉 ## ADDED Requirements header
```

#### 6. 文件夹管理规范

1.  **命名规范**：变更文件夹命名使用**小写字母 + 短横线（kebab-case）**，如 `add-user-profile`、`fix-checkout-total`。禁止使用空格或下划线。
2.  **及时清理**：对于已放弃的变更（不再实施的），开发者需主动删除 `openspec/changes/<变更名>/` 文件夹，或使用 `openspec change delete <变更名>` 命令清理。
3.  **一周一归档**：建议每周五进行团队提醒，检查是否有遗留的未归档变更。

#### 7. 记录关键决策

在 `/opsx:explore` 讨论或 `/opsx:apply` 实施过程中，如果做了有意义的架构决策（选 A 弃 B 的原因、新发现的风险、颠覆原设计的信息），应记录下来：

- **小决策**：追加到 `design.md` 的对应 section，或补充在 `## 讨论回顾` 中
- **大决策**：在 `proposal.md` 中更新 "What Changes" 或 "Impact"
- **值得保留的通用知识**：写入 `openspec/GUIDELINES.md` 或更新项目 README/CLAUDE.md

**为什么需要记**：开发时的"当时为什么这么设计"在 3 个月后不会有人记得。花 30 秒写一句话可以省掉未来数小时的考古。

#### 8. 例外处理（紧急情况）

如遇线上紧急 Hotfix，可以**先修 Bug，后补提案**。但须在修复后 **24 小时内**，创建一个归档变更（如 `post-hotfix-xxx`）来记录这次修改的上下文，并更新主规范。