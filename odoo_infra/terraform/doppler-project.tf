resource "doppler_project" "netcup_stack" {
  name        = "netcup-stack"
  description = "Main netcup stack project for Odoo instances and related secrets"
}

resource "doppler_environment" "environments" {
  for_each = toset(local.environments)

  project          = doppler_project.netcup_stack.name
  slug             = each.value
  name             = "${each.value} Environment"
  personal_configs = false
}

resource "doppler_service_token" "service_tokens" {
  for_each = doppler_config.environment_branch_configs

  project = doppler_project.netcup_stack.name
  config  = each.value.name
  name    = "${doppler_project.netcup_stack.name}-${each.key}"
  access  = "read"
}

resource "doppler_config" "environment_configs" {
  for_each = doppler_environment.environments

  project     = doppler_project.netcup_stack.name
  environment = each.value.slug
  name        = each.value.slug
  inheritable = false
}

resource "doppler_config" "environment_branch_configs" {
  for_each = local.env_branch_map

  project     = doppler_project.netcup_stack.name
  environment = each.value.env
  name        = "${each.value.env}_${each.value.branch}"
  inheritable = false
}

resource "doppler_secret" "secrets" {
  for_each = local.branch_secret_map

  project = doppler_project.netcup_stack.name
  config  = doppler_config.environment_branch_configs["${each.value.environment}.${each.value.branch}"].name
  name    = each.value.secret
  value = contains(local.shared_secrets, each.value.secret) ? (
    contains(keys(local.shared_custom_values), each.value.secret)
    ? local.shared_custom_values[each.value.secret]
    : random_password.shared_secrets[each.value.secret].result
    ) : (
    each.value.value != null
    ? each.value.value
    : random_password.project_secrets[each.value.random_key].result
  )
}

resource "random_password" "shared_secrets" {
  for_each = local.shared_random_secrets

  length  = 32
  special = false
}

resource "random_password" "project_secrets" {
  for_each = local.project_random_secrets

  length  = 32
  special = true
  override_special = "-_." # Avoid characters that might cause issues in certain contexts (e.g., URLs, config files)
}

locals {
  branches = {
    production = ["core", "business", "ai"]
  }
  environments = keys(local.branches)

  environment_branches = flatten([
    for env, branches in local.branches : [
      for branch in branches : {
        id     = "${env}.${branch}"
        env    = env
        branch = branch
      }
    ]
  ])

  env_branch_map = {
    for item in local.environment_branches : item.id => item
  }

  # Supports both the legacy list format and the new object format:
  # business = {
  #   N8N_HOST = { value = "https://n8n.example.com" }
  #   ODOO_ADMIN_PASSWD = {}
  # }
  secrets = {
    production = {
      core = {
        POSTGRES_PASSWORD = {}
        ODOO_DB_PASSWORD  = {}
        N8N_DB_PASSWORD   = {}
        PGADMIN_EMAIL     = {
          value = "snobljan@gmail.com"
        }
        PGADMIN_PASSWORD  = {}
      }
      business = {
        ODOO_DB_PASSWORD   = {}
        ODOO_ADMIN_PASSWD  = {}
        N8N_DB_PASSWORD    = {}
        N8N_ENCRYPTION_KEY = {}
        N8N_HOST           = {}
        N8N_WEBHOOK_URL    = {}
        CF_TUNNEL_TOKEN    = {}
      }
      ai = {
        OPENAI_API_KEY      = {}
        OPENAI_API_BASE_URL = {}
        WEBUI_SECRET_KEY    = {}
      }
    }
  }

  normalized_secrets = {
    for environment, branches in local.secrets : environment => {
      for branch, secrets in branches : branch => (
        can(keys(secrets))
        ? { for secret_name, secret_config in secrets : secret_name => (secret_config == null ? {} : secret_config) }
        : { for secret_name in secrets : secret_name => {} }
      )
    }
  }

  branch_secrets = flatten([
    for environment, branches in local.normalized_secrets : [
      for branch, secrets in branches : [
        for secret_name, secret_config in secrets : {
          id          = "${environment}.${branch}.${secret_name}"
          environment = environment
          branch      = branch
          secret      = secret_name
          value       = try(secret_config.value, null)
          ## value_type and visibility can be added here in the future if needed, e.g.:
        }
      ]
    ]
  ])

  project_secret_occurrences = {
    for secret_name in distinct([
      for item in local.branch_secrets : item.secret
      if !contains(local.shared_secrets, item.secret)
      ]) : secret_name => length([
      for item in local.branch_secrets : item.id
      if item.secret == secret_name && !contains(local.shared_secrets, item.secret)
    ])
  }

  branch_secret_map = {
    for item in local.branch_secrets : item.id => merge(item, {
      random_key = contains(local.shared_secrets, item.secret) ? item.secret : (
        local.project_secret_occurrences[item.secret] > 1 ? item.id : item.secret
      )
    })
  }

  shared_secrets = [
    "ODOO_DB_PASSWORD",
    "N8N_DB_PASSWORD",
    "MEDUSA_DB_PASSWORD",
    "PHP_TAROT_CARDS_DB_PASSWORD",
  ]

  shared_custom_values = {
    for secret in local.shared_secrets :
    secret => one(distinct([
      for item in local.branch_secrets : item.value
      if item.secret == secret && item.value != null
    ]))
    if length(distinct([
      for item in local.branch_secrets : item.value
      if item.secret == secret && item.value != null
    ])) > 0
  }

  shared_random_secrets = toset(local.shared_secrets)

  project_random_secrets = {
    for key, item in local.branch_secret_map : item.random_key => item
    if item.value == null && !contains(local.shared_secrets, item.secret)
  }
}
