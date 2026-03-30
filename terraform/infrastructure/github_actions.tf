resource "aws_ecr_repository" "extraction_ecr_repository" {
  name = var.extraction_ecr_repo_name
  force_delete = true
}

resource "aws_ecrpublic_repository" "backend_ecr_repository" {
  repository_name = var.backend_ecr_repo_name
  force_destroy = true
}

resource "aws_ecrpublic_repository" "frontend_ecr_repository" {
  repository_name = var.frontend_ecr_repo_name
  force_destroy = true
}

# Created in other workspace
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "github_assume_role_policy_document" {
  statement {
    effect = "Allow"
    principals {
      type = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }
    actions = ["sts:AssumeRoleWithWebIdentity"]
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_repo}:*"
      ]
    }
  }
}

resource "aws_iam_role" "role_for_infrastructure_update" {
  name               = var.name_of_role_for_infrastructure_update
  assume_role_policy = data.aws_iam_policy_document.github_assume_role_policy_document.json
  path               = var.path_of_role_for_infrastructure_update
}

data "aws_iam_policy_document" "ecr_policy_document" {
  statement {
    effect = "Allow"

    actions = [
      "ecr:GetAuthorizationToken"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
      "ecr:BatchGetImage",
      "ecr:GetRepositoryPolicy",
      "ecr:SetRepositoryPolicy"
    ]

    resources = [
      aws_ecr_repository.extraction_ecr_repository.arn
    ]
  }
}

resource "aws_iam_policy" "ecr_policy" {
  name   = "ecr-policy"
  policy = data.aws_iam_policy_document.ecr_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_ecr" {
  role       = aws_iam_role.role_for_infrastructure_update.name
  policy_arn = aws_iam_policy.ecr_policy.arn
}

data "aws_iam_policy_document" "ecr_public_policy_document" {
  statement {
    effect = "Allow"

    actions = [
      "ecr-public:GetAuthorizationToken",
      "sts:GetServiceBearerToken"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "ecr-public:BatchCheckLayerAvailability",
      "ecr-public:CompleteLayerUpload",
      "ecr-public:InitiateLayerUpload",
      "ecr-public:PutImage",
      "ecr-public:UploadLayerPart",
      "ecr-public:DescribeImages",
      "ecr-public:GetRepositoryPolicy",
      "ecr-public:SetRepositoryPolicy"
    ]

    resources = [
      aws_ecrpublic_repository.backend_ecr_repository.arn,
      aws_ecrpublic_repository.frontend_ecr_repository.arn
    ]
  }
}

resource "aws_iam_policy" "ecr_public_policy" {
  name   = "ecr-public-policy"
  policy = data.aws_iam_policy_document.ecr_public_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_ecr_public" {
  role       = aws_iam_role.role_for_infrastructure_update.name
  policy_arn = aws_iam_policy.ecr_public_policy.arn
}

data "aws_iam_policy_document" "ssm_command_policy_document" {
  statement {
    effect = "Allow"

    actions = [
      "ssm:SendCommand",
      "ssm:GetCommandInvocation"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_policy" "ssm_command_policy" {
  name   = "ssm-command-policy"
  policy = data.aws_iam_policy_document.ssm_command_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_ssm_command_to_github_role" {
  role       = aws_iam_role.role_for_infrastructure_update.name
  policy_arn = aws_iam_policy.ssm_command_policy.arn
}

data "aws_iam_policy_document" "ssm_policy_document" {
  statement {
    effect = "Allow"

    actions = [
      "ssm:PutParameter",
    ]

    resources = [
      "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/*"
    ]
  }
}

resource "aws_iam_policy" "ssm_policy" {
  name   = "github-actions-ssm-policy"
  policy = data.aws_iam_policy_document.ssm_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_ssm_policy_to_github_role" {
  role       = aws_iam_role.role_for_infrastructure_update.name
  policy_arn = aws_iam_policy.ssm_policy.arn
}
