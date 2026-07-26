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
    cutto = group("Cutto")
    custom_direct = group("海外自定义直连组")
    custom_proxy = group("海外自定义代理组")

    refute_nil cutto
    refute_nil custom_direct
    refute_nil custom_proxy
    assert_equal "默认", cutto.fetch("proxies").first
    assert_equal ["直连", "默认"], custom_direct.fetch("proxies")
    assert_equal "默认", custom_proxy.fetch("proxies").first
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
    assert providers.key?("overseas_custom_direct_classical")
    assert providers.key?("overseas_custom_proxy_classical")
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
