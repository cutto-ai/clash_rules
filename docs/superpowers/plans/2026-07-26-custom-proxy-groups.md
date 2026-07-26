# Custom Proxy Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add visible Cutto and overseas custom policy groups while replacing the old SaaS rule names and raw URLs with the approved English naming.

**Architecture:** Keep `stash` as the single Clash configuration and keep each custom domain collection in one YAML rule file. Treat proxy-group definitions, `RULE-SET` routes, provider definitions, and rule-file paths as one atomic change, backed by a dependency-free Ruby/Minitest structural validator.

**Tech Stack:** Clash YAML, Ruby 2.6+ standard library (`yaml`, `minitest`), Git.

## Global Constraints

- The visible groups are exactly `Cutto`, `海外自定义直连组`, and `海外自定义代理组`.
- `海外自定义直连组` is a selector whose ordered choices are exactly `直连`, `默认`.
- `Cutto` and `海外自定义代理组` reuse the existing `*pr` selector options.
- Rename the SaaS files and providers to `overseas_custom_direct` and `overseas_custom_proxy`; do not retain compatibility aliases.
- New provider URLs use `https://raw.githubusercontent.com/cutto-ai/clash_rules/refs/heads/main/rules/`.
- Preserve both renamed files' payload content and preserve the existing rule priority before `GEOIP,CN`.
- Do not modify unrelated groups, rules, providers, or domain payloads.

---

### Task 1: Implement and validate the three custom proxy groups

**Files:**
- Create: `tests/validate_config.rb`
- Modify: `stash:37-241`
- Rename: `rules/saas_direct.list` → `rules/overseas_custom_direct.list`
- Rename: `rules/saas_proxy.list` → `rules/overseas_custom_proxy.list`

**Interfaces:**
- Consumes: `stash` keys `proxy-groups`, `rules`, and `rule-providers`; rule files with top-level `payload` arrays.
- Produces: proxy groups `Cutto`, `海外自定义直连组`, `海外自定义代理组`; providers `cutto_classical`, `overseas_custom_direct_classical`, `overseas_custom_proxy_classical`; matching rule-file paths and raw URLs.

- [ ] **Step 1: Write the failing structural test**

Create `tests/validate_config.rb` with this complete content:

```ruby
# frozen_string_literal: true

require "minitest/autorun"
require "yaml"

ROOT = File.expand_path("..", __dir__)
CONFIG_PATH = File.join(ROOT, "stash")
CONFIG = YAML.load_file(CONFIG_PATH)

class ConfigValidationTest < Minitest::Test
  EXPECTED_DIRECT_PAYLOAD = [
    "DOMAIN-KEYWORD,typeless",
    "DOMAIN-SUFFIX,linear.app",
    "DOMAIN-SUFFIX,linearstatus.com",
    "DOMAIN-SUFFIX,stripe.com",
    "DOMAIN-SUFFIX,stripecdn.com",
    "DOMAIN-SUFFIX,stripe.network",
    "DOMAIN-SUFFIX,stripeassets.com"
  ].freeze

  EXPECTED_PROXY_PAYLOAD = [
    "DOMAIN-SUFFIX,manus.im",
    "DOMAIN-SUFFIX,manus.ai",
    "DOMAIN-SUFFIX,manuscdn.com",
    "DOMAIN-SUFFIX,cursor.sh",
    "DOMAIN-SUFFIX,cursor.com",
    "DOMAIN-SUFFIX,cursorapi.com",
    "DOMAIN-SUFFIX,cursor-cdn.com"
  ].freeze

  def groups
    CONFIG.fetch("proxy-groups")
  end

  def group(name)
    groups.find { |entry| entry["name"] == name }
  end

  def providers
    CONFIG.fetch("rule-providers")
  end

  def rules
    CONFIG.fetch("rules")
  end

  def test_new_groups_replace_saas
    assert_equal 1, groups.count { |entry| entry["name"] == "Cutto" }
    assert_equal 1, groups.count { |entry| entry["name"] == "海外自定义直连组" }
    assert_equal 1, groups.count { |entry| entry["name"] == "海外自定义代理组" }
    refute groups.any? { |entry| entry["name"] == "SaaS" }
  end

  def test_group_defaults_and_choices
    assert_equal "默认", group("Cutto").fetch("proxies").first
    assert_equal ["直连", "默认"], group("海外自定义直连组").fetch("proxies")
    assert_equal "默认", group("海外自定义代理组").fetch("proxies").first
  end

  def test_custom_rules_target_new_groups_before_geoip_cn
    expected = [
      "RULE-SET,overseas_custom_direct_classical,海外自定义直连组",
      "RULE-SET,overseas_custom_proxy_classical,海外自定义代理组"
    ]
    geoip_cn_index = rules.index("GEOIP,CN,直连,no-resolve")

    expected.each do |rule|
      assert_includes rules, rule
      assert_operator rules.index(rule), :<, geoip_cn_index
    end
    assert_includes rules, "RULE-SET,cutto_classical,Cutto"
    refute rules.any? { |rule| rule.include?("saas_") }
  end

  def test_new_providers_and_urls_replace_saas
    assert_equal(
      "https://raw.githubusercontent.com/cutto-ai/clash_rules/refs/heads/main/rules/overseas_custom_direct.list",
      providers.fetch("overseas_custom_direct_classical").fetch("url")
    )
    assert_equal(
      "https://raw.githubusercontent.com/cutto-ai/clash_rules/refs/heads/main/rules/overseas_custom_proxy.list",
      providers.fetch("overseas_custom_proxy_classical").fetch("url")
    )
    refute providers.key?("saas_direct_classical")
    refute providers.key?("saas_proxy_classical")
  end

  def test_every_rule_set_has_a_provider
    referenced = rules.each_with_object([]) do |rule, names|
      fields = rule.split(",")
      names << fields[1] if fields.first == "RULE-SET"
    end

    assert_empty referenced.uniq - providers.keys
  end

  def test_rule_files_are_renamed_without_payload_changes
    direct_path = File.join(ROOT, "rules", "overseas_custom_direct.list")
    proxy_path = File.join(ROOT, "rules", "overseas_custom_proxy.list")

    assert File.exist?(direct_path)
    assert File.exist?(proxy_path)
    refute File.exist?(File.join(ROOT, "rules", "saas_direct.list"))
    refute File.exist?(File.join(ROOT, "rules", "saas_proxy.list"))
    assert_equal EXPECTED_DIRECT_PAYLOAD, YAML.load_file(direct_path).fetch("payload")
    assert_equal EXPECTED_PROXY_PAYLOAD, YAML.load_file(proxy_path).fetch("payload")
  end
end
```

- [ ] **Step 2: Run the test and verify the current configuration fails**

Run:

```bash
ruby tests/validate_config.rb
```

Expected: FAIL because the three approved groups and renamed files/providers do not yet exist, while `SaaS` and `saas_*` still exist.

- [ ] **Step 3: Rename the rule files without changing payloads**

Run:

```bash
git mv rules/saas_direct.list rules/overseas_custom_direct.list
git mv rules/saas_proxy.list rules/overseas_custom_proxy.list
```

- [ ] **Step 4: Replace the proxy groups in `stash`**

Replace the current `SaaS` group with these three entries immediately after `OpenAI`:

```yaml
- {name: Cutto, <<: *pr, icon: "https://raw.githubusercontent.com/Koolson/Qure/refs/heads/master/IconSet/mini/AIA.png"}
- {name: 海外自定义直连组, type: select, proxies: [直连, 默认], icon: "https://raw.githubusercontent.com/Koolson/Qure/refs/heads/master/IconSet/mini/AIA.png"}
- {name: 海外自定义代理组, <<: *pr, icon: "https://raw.githubusercontent.com/Koolson/Qure/refs/heads/master/IconSet/mini/AIA.png"}
```

- [ ] **Step 5: Replace the custom rule routes in `stash`**

Keep the two overseas custom rules before `GEOIP,CN` and use these exact entries:

```yaml
- RULE-SET,overseas_custom_direct_classical,海外自定义直连组
- RULE-SET,overseas_custom_proxy_classical,海外自定义代理组
```

Change the Cutto route to:

```yaml
- RULE-SET,cutto_classical,Cutto
```

- [ ] **Step 6: Replace the provider definitions and raw URLs in `stash`**

Replace the two `saas_*` providers with:

```yaml
  overseas_custom_direct_classical:
    <<: *classical
    url: "https://raw.githubusercontent.com/cutto-ai/clash_rules/refs/heads/main/rules/overseas_custom_direct.list"
  overseas_custom_proxy_classical:
    <<: *classical
    url: "https://raw.githubusercontent.com/cutto-ai/clash_rules/refs/heads/main/rules/overseas_custom_proxy.list"
```

- [ ] **Step 7: Run the structural test and verify it passes**

Run:

```bash
ruby tests/validate_config.rb
```

Expected: 6 runs, 0 failures, 0 errors.

- [ ] **Step 8: Run final static checks**

Run:

```bash
ruby -e 'require "yaml"; YAML.load_file("stash"); puts "YAML OK"'
git diff --check
rg -n 'SaaS|saas_direct|saas_proxy' stash rules
```

Expected: YAML prints `YAML OK`; `git diff --check` exits 0; `rg` exits 1 with no matches in `stash` or `rules`. Legacy names remain only in test assertions that verify their removal.

- [ ] **Step 9: Review the exact diff**

Run:

```bash
git status --short
git diff -- stash rules tests
```

Expected: one test file created, `stash` modified only in the approved group/rule/provider entries, and two rule files shown as renames with unchanged payloads.

- [ ] **Step 10: Commit the atomic implementation**

Run:

```bash
git add stash tests/validate_config.rb rules
git commit -m "feat: add custom proxy groups"
```
