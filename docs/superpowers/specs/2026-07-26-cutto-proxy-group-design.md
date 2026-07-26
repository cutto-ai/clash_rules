# Cutto 代理组设计

## 目标

让 Clash Verge 的代理组页面显示 `Cutto`，并允许用户为 Cutto 域名选择通用代理策略。

## 设计

- 在 `stash` 的 `proxy-groups` 中新增 `Cutto` selector。
- `Cutto` 复用现有 `*pr` 锚点，使其可选项与 `SaaS` 等通用代理组一致。
- 将 `RULE-SET,cutto_classical,直连` 改为 `RULE-SET,cutto_classical,Cutto`。
- 保留 `rules/cutto.list` 与 `cutto_classical` provider，不改变域名范围和远程地址。

## 数据流

请求命中 `rules/cutto.list` 后，由 `cutto_classical` 规则集转交给 `Cutto` 代理组，再按用户在 Clash Verge 中选择的策略处理。

## 兼容性与失败处理

- 组名和规则目标必须完全一致，否则 Clash 无法加载或不会按预期路由。
- 继续使用已有 YAML 锚点和单行 proxy-group 格式，避免引入新的配置结构。
- 不修改其他代理组、规则顺序或 provider。

## 验证

- YAML 能成功解析。
- `proxy-groups` 中恰好存在一个名为 `Cutto` 的组。
- `cutto_classical` 规则目标为 `Cutto`，且不再固定为 `直连`。
- `cutto_classical` provider 仍存在并引用 `rules/cutto.list`。
- Git diff 仅包含设计文档和上述两处配置变更。
