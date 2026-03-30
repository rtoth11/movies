terraform {
  cloud {
    organization = "movies"
    workspaces {
      name = "role_for_infrastructure_creation"
    }
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.38"
    }
  }

  required_version = ">= 1.2"
}
