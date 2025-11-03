provider "aws" {
  region = "us-east-1"
  #profile = ""
}

data "tls_certificate" "hcp_terraform_tls_cert_provider" {
  url = "https://app.terraform.io"
}

resource "aws_iam_openid_connect_provider" "hcp_terraform_oidc_provider" {
  url = "https://app.terraform.io"

  client_id_list = [
    "aws.workload.identity"
  ]

  thumbprint_list = [
    data.tls_certificate.hcp_terraform_tls_cert_provider.certificates[0].sha1_fingerprint
  ]
}

data "aws_iam_policy_document" "hcp_terraform_assume_role_policy_document" {
  statement {
    effect = "Allow"

    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type = "Federated"
      identifiers = [aws_iam_openid_connect_provider.hcp_terraform_oidc_provider.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "app.terraform.io:aud"
      values   = ["aws.workload.identity"]
    }

    condition {
      test     = "StringLike"
      variable = "app.terraform.io:sub"
      values   = [
        "organization:${local.hcp_terraform_infrastructure_organization}:project:${local.hcp_terraform_infrastructure_project}:workspace:${local.hcp_terraform_infrastructure_workspace_name}:run_phase:*"
      ]
    }
  }
}

resource "aws_iam_role" "hcp_terraform_role" {
  name               = var.hcp_terraform_role_name
  assume_role_policy = data.aws_iam_policy_document.hcp_terraform_assume_role_policy_document.json
  path               = var.hcp_terraform_role_path
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "terraform_policy_document" {
  statement {
    effect = "Allow"

    actions = [
      "events:DeleteRule",
      "events:DescribeRule",
      "events:ListTagsForResource",
      "events:ListTargetsByRule",
      "events:PutRule",
      "events:PutTargets",
      "events:RemoveTargets",
      "s3:CreateBucket",
      "s3:DeleteBucket",
      "s3:ListBucket",
      "s3:GetAccelerateConfiguration",
      "s3:GetBucketLogging",
      "s3:GetBucketObjectLockConfiguration",
      "s3:GetBucketRequestPayment",
      "s3:GetBucketTagging",
      "s3:GetBucketVersioning",
      "s3:GetBucketWebsite",
      "s3:GetEncryptionConfiguration",
      "s3:GetLifecycleConfiguration",
      "s3:GetReplicationConfiguration",
      "s3:GetBucketAcl",
      "s3:GetBucketCORS",
      "s3:GetBucketPolicy",
      "sts:GetCallerIdentity"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "ecr:CreateRepository",
      "ecr:DeleteRepository",
      "ecr:DescribeRepositories",
      "ecr:GetRepositoryPolicy",
      "ecr:ListTagsForResource",
      "ecr:SetRepositoryPolicy",
      "ecr:TagResource"
    ]

    resources = [
      "arn:aws:ecr:${var.region}:${data.aws_caller_identity.current.account_id}:repository/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "iam:CreateOpenIDConnectProvider",
      "iam:DeleteOpenIDConnectProvider",
      "iam:GetOpenIDConnectProvider"
    ]

    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "iam:CreatePolicy",
      "iam:DeletePolicy",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListPolicyVersions"
    ]

    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "iam:AttachRolePolicy",
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:DetachRolePolicy",
      "iam:GetRole",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListRolePolicies",
      "iam:PassRole"
    ]

    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "lambda:AddPermission",
      "lambda:CreateFunction",
      "lambda:DeleteFunction",
      "lambda:GetFunction",
      "lambda:GetPolicy",
      "lambda:ListVersionsByFunction",
      "lambda:RemovePermission"
    ]

    resources = [
      "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:*"
    ]
  }
}

resource "aws_iam_policy" "terraform_policy" {
  name   = "terraform-policy"
  policy = data.aws_iam_policy_document.terraform_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_terraform_to_hcp_terraform_role" {
  role       = aws_iam_role.hcp_terraform_role.name
  policy_arn = aws_iam_policy.terraform_policy.arn
}
