resource "aws_ecr_repository" "ingestion_ecr_repository" {
  name = var.ingestion_ecr_repo_name
  force_delete = true
}

resource "aws_iam_openid_connect_provider" "github_oidc_provider" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]
}

data "aws_iam_policy_document" "github_assume_role_policy_document" {
  statement {
    effect = "Allow"
    principals {
      type = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_oidc_provider.arn]
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

resource "aws_iam_role" "github_actions_role" {
  name               = var.github_role_name
  assume_role_policy = data.aws_iam_policy_document.github_assume_role_policy_document.json
  path               = var.github_role_path
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
      aws_ecr_repository.ingestion_ecr_repository.arn
    ]
  }
}

resource "aws_iam_policy" "ecr_policy" {
  name   = "ecr-policy"
  policy = data.aws_iam_policy_document.ecr_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_ecr_to_github_role" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = aws_iam_policy.ecr_policy.arn
}

data "aws_iam_policy_document" "lambda_update_function_policy_document" {
  statement {
    effect = "Allow"

    actions = [
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration"
    ]
    resources = [
      aws_lambda_function.ingestion_lambda.arn
    ]
  }
}

resource "aws_iam_policy" "lambda_update_function_policy" {
  name   = "lambda-update-function-policy"
  policy = data.aws_iam_policy_document.lambda_update_function_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_lambda_update_function_to_github_role" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = aws_iam_policy.lambda_update_function_policy.arn
}
