terraform {
  cloud {
    organization = "movies"
    workspaces {
      name = "infrastructure"
    }
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.33"
    }
  }

  required_version = ">= 1.2"
}
