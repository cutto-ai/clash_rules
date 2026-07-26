# 自定义代理组与规则重命名设计

## 目标

让 Clash Verge 显示 `Cutto`、`海外自定义直连组` 和 `海外自定义代理组` 三个独立代理组，并用语义一致的英文名称替换现有 SaaS 规则文件与 provider。

## 代理组设计

| 代理组 | 类型与候选策略 | 默认策略 |
| --- | --- | --- |
| `Cutto` | 复用 `*pr`，提供通用代理策略 | `默认` |
| `海外自定义直连组` | `select`，候选项为 `直连`、`默认` | `直连` |
| `海外自定义代理组` | 复用 `*pr`，提供通用代理策略 | `默认` |

删除现有 `SaaS` 代理组，不保留兼容代理组。

## 规则与 provider 映射

| 规则文件 | Provider | 目标代理组 |
| --- | --- | --- |
| `rules/cutto.list` | `cutto_classical` | `Cutto` |
| `rules/overseas_custom_direct.list` | `overseas_custom_direct_classical` | `海外自定义直连组` |
| `rules/overseas_custom_proxy.list` | `overseas_custom_proxy_classical` | `海外自定义代理组` |

现有文件按 Git 重命名处理：

- `rules/saas_direct.list` 重命名为 `rules/overseas_custom_direct.list`。
- `rules/saas_proxy.list` 重命名为 `rules/overseas_custom_proxy.list`。

不保留旧规则路径或旧的 `saas_direct_classical`、`saas_proxy_classical` provider 名称。

## Raw URL

新 provider 统一引用 `cutto-ai/clash_rules` 的 `main` 分支：

```text
https://raw.githubusercontent.com/cutto-ai/clash_rules/refs/heads/main/rules/overseas_custom_direct.list
https://raw.githubusercontent.com/cutto-ai/clash_rules/refs/heads/main/rules/overseas_custom_proxy.list
```

配置不再引用 `Colsrch/clash_rules` 下的旧 SaaS URL。变更合入 `main` 后，新 raw URL 才会生效；旧 URL 不提供兼容保证。

## 数据流

- 命中 `cutto_classical` 的请求进入 `Cutto`，使用用户选择的通用代理策略。
- 命中 `overseas_custom_direct_classical` 的请求进入 `海外自定义直连组`，默认直连，也可切换到 `默认`。
- 命中 `overseas_custom_proxy_classical` 的请求进入 `海外自定义代理组`，默认使用 `默认`，也可选择其他通用代理策略。

三条规则保持在 `GEOIP,CN` 之前，延续当前海外自定义规则的优先级。

## 兼容性与失败处理

- 代理组名称、规则目标和 provider 名称必须完全一致，否则 Clash 无法加载或不会按预期路由。
- 新 provider URL 在对应规则文件合入 `main` 前会返回 404，因此配置与重命名文件必须在同一变更中发布。
- 不改变规则文件的 payload 内容、Cutto 域名范围、其他代理组或其他 provider。
- 更新订阅后，用户原来为 `SaaS` 保存的选择不会迁移到两个新中文代理组，需要重新选择。

## 验证

- 完整配置可被 YAML 解析。
- 三个新代理组各存在且仅存在一次，`SaaS` 代理组不存在。
- `海外自定义直连组` 的候选顺序为 `直连`、`默认`。
- 三条 `RULE-SET` 分别指向正确的代理组。
- 所有自定义 `RULE-SET` 都能解析到已定义 provider，所有新 provider 都指向对应的新规则文件。
- 新旧规则文件、provider 名称和 URL 不混用；仓库中不存在旧 `saas_direct.list`、`saas_proxy.list`。
- 两个重命名文件的 payload 与重命名前保持一致。
- Git diff 不包含本需求之外的配置或规则内容修改。
