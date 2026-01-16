provider "aws" {
  region = "us-east-1"
  #profile = ""
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

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "first_terraform_policy_document" {
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
      "s3:DeleteObject",
      "s3:DeleteObjectVersion",
      "s3:ListBucket",
      "s3:ListBucketVersions",
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
      "sts:GetCallerIdentity",
      "ec2:CreateVpc",
      "ec2:ModifyVpcAttribute",
      "ec2:DescribeVpcs",
      "ec2:DeleteVpc",
      "ec2:CreateTags",
      "ec2:DescribeVpcAttribute",
      "ec2:CreateSubnet",
      "ec2:DescribeSubnets",
      "ec2:DeleteSubnet",
      "ec2:ModifySubnetAttribute",
      "ec2:CreateInternetGateway",
      "ec2:DescribeInternetGateways",
      "ec2:DeleteInternetGateway",
      "ec2:AttachInternetGateway",
      "ec2:DetachInternetGateway",
      "ec2:CreateRouteTable",
      "ec2:DescribeRouteTables",
      "ec2:DeleteRouteTable",
      "ec2:CreateRoute",
      "ec2:DeleteRoute",
      "ec2:AssociateRouteTable",
      "ec2:DisassociateRouteTable",
      "ec2:CreateSecurityGroup",
      "ec2:DescribeSecurityGroups",
      "ec2:DeleteSecurityGroup",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:RevokeSecurityGroupIngress",
      "ec2:AuthorizeSecurityGroupEgress",
      "ec2:RevokeSecurityGroupEgress",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DescribeAvailabilityZones",
      "ec2:DescribeAccountAttributes",
      "ec2:DescribeNetworkAcls",
      "ec2:DescribeImages",
      "ec2:DescribeLaunchTemplates",
      "ec2:DescribeLaunchTemplateVersions",
      "ec2:DescribeAutoScalingGroups",
      "ec2:DescribeTags",
      "ec2:RunInstances",
      "ec2:TerminateInstances",
      "rds:CreateDBInstance",
      "rds:ModifyDBInstance",
      "rds:DeleteDBInstance",
      "rds:DescribeDBInstances",
      "rds:CreateDBSubnetGroup",
      "rds:DeleteDBSubnetGroup",
      "rds:DescribeDBSubnetGroups",
      "rds:ListTagsForResource",
      "rds:AddTagsToResource",
      "rds:RemoveTagsFromResource",
      "rds:AddRoleToDBInstance",
      "rds:RemoveRoleFromDBInstance",
      "elasticloadbalancing:DescribeTargetGroups",
      "elasticloadbalancing:DescribeTargetGroupAttributes",
      "elasticloadbalancing:DescribeTags",
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeLoadBalancerAttributes",
      "elasticloadbalancing:DescribeListeners",
      "elasticloadbalancing:DescribeListenerAttributes",
      "elasticloadbalancing:DescribeRules",
      "ecs:ListClusters",
      "ecs:DescribeClusters",
      "ecs:DescribeServices",
      "ecs:ListTaskDefinitions",
      "ecs:DescribeTasks",
      "ecs:RegisterTaskDefinition",
      "ecs:DescribeTaskDefinition",
      "ecs:DeregisterTaskDefinition",
      "ecs:CreateService",
      "ecs:UpdateService",
      "ecs:DeleteService",
      "ecs:DescribeServices",
      "ecs:ListServices",
      "ecr-public:DescribeRepositories",
      "iam:ListOpenIDConnectProviders",
      "iam:GetInstanceProfile",
      "ssm:GetParameters",
      "autoscaling:DescribeAutoScalingGroups",
      "autoscaling:DescribeAutoScalingActivities",
      "autoscaling:DescribeLaunchConfigurations",
      "autoscaling:DescribeScalingActivities",
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:PutRetentionPolicy",
      "logs:DescribeLogGroups",
      "logs:ListTagsForResource"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "first_terraform_policy" {
  name   = "first-terraform-policy"
  policy = data.aws_iam_policy_document.first_terraform_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_first_terraform_to_github_actions_role" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = aws_iam_policy.first_terraform_policy.arn
}

data "aws_iam_policy_document" "second_terraform_policy_document" {
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
      "iam:ListPolicyVersions",
      "iam:CreatePolicyVersion",
      "iam:DeletePolicyVersion"
    ]

    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListPolicyVersions"
    ]

    resources = [
      "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
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
      "iam:PassRole",
      "iam:CreateServiceLinkedRole"
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
      "lambda:RemovePermission",
      "lambda:UpdateFunctionCode",
      "lambda:GetFunctionEventInvokeConfig",
      "lambda:PutFunctionEventInvokeConfig",
      "lambda:ListFunctionEventInvokeConfigs",
      "lambda:DeleteFunctionEventInvokeConfig",
      "lambda:UpdateFunctionEventInvokeConfig",
      "lambda:UpdateFunctionConfiguration"
    ]

    resources = [
      "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "ecs:CreateCluster",
      "ecs:DeleteCluster"
    ]

    resources = [
      "arn:aws:ecs:${var.region}:${data.aws_caller_identity.current.account_id}:cluster/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "ecr-public:CreateRepository",
      "ecr-public:DeleteRepository",
      "ecr-public:GetRepositoryCatalogData",
      "ecr-public:ListTagsForResource",
      "ecr-public:TagResource"
    ]

    resources = [
      "arn:aws:ecr-public::${data.aws_caller_identity.current.account_id}:repository/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "elasticloadbalancing:CreateLoadBalancer",
      "elasticloadbalancing:DeleteLoadBalancer",
      "elasticloadbalancing:ModifyLoadBalancerAttributes",
      "elasticloadbalancing:CreateListener",
      "elasticloadbalancing:DeleteListener",
      "elasticloadbalancing:ModifyListener"
    ]

    resources = [
      "arn:aws:elasticloadbalancing:${var.region}:${data.aws_caller_identity.current.account_id}:loadbalancer/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "elasticloadbalancing:CreateTargetGroup",
      "elasticloadbalancing:DeleteTargetGroup",
      "elasticloadbalancing:RegisterTargets",
      "elasticloadbalancing:DeregisterTargets",
      "elasticloadbalancing:ModifyTargetGroupAttributes"
    ]

    resources = [
      "arn:aws:elasticloadbalancing:${var.region}:${data.aws_caller_identity.current.account_id}:targetgroup/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "elasticloadbalancing:DeleteListener",
      "elasticloadbalancing:ModifyListener",
      "elasticloadbalancing:CreateRule",
      "elasticloadbalancing:DeleteRule"
    ]

    resources = [
      "arn:aws:elasticloadbalancing:${var.region}:${data.aws_caller_identity.current.account_id}:listener/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "elasticloadbalancing:DeleteRule"
    ]

    resources = [
      "arn:aws:elasticloadbalancing:${var.region}:${data.aws_caller_identity.current.account_id}:listener-rule/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "iam:CreateInstanceProfile",
      "iam:DeleteInstanceProfile",
      "iam:AddRoleToInstanceProfile",
      "iam:RemoveRoleFromInstanceProfile"
    ]

    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:instance-profile/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DeleteNetworkInterface",
      "ec2:ModifyNetworkInterfaceAttribute"
    ]

    resources = [
      "arn:aws:ec2:${var.region}:${data.aws_caller_identity.current.account_id}:network-interface/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "ec2:createLaunchTemplate",
      "ec2:deleteLaunchTemplate",
      "ec2:modifyLaunchTemplate",
      "ec2:createLaunchTemplateVersion",
      "ec2:deleteLaunchTemplateVersions"
    ]

    resources = [
      "arn:aws:ec2:${var.region}:${data.aws_caller_identity.current.account_id}:launch-template/*"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "autoscaling:createAutoScalingGroup",
      "autoscaling:deleteAutoScalingGroup",
      "autoscaling:updateAutoScalingGroup",
      "autoscaling:enableMetricsCollection",
      "autoscaling:disableMetricsCollection"
    ]

    resources = [
      "arn:aws:autoscaling:${var.region}:${data.aws_caller_identity.current.account_id}:autoScalingGroup:*:autoScalingGroupName/*"
    ]
  }
}

resource "aws_iam_policy" "second_terraform_policy" {
  name   = "second-terraform-policy"
  policy = data.aws_iam_policy_document.second_terraform_policy_document.json
}

resource "aws_iam_role_policy_attachment" "attach_second_terraform_to_github_actions_role" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = aws_iam_policy.second_terraform_policy.arn
}
