terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = "zt-agentic-${var.environment}"
}

# VPC with micro-segmentation
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "5.8.1"

  name = "${local.name_prefix}-vpc"
  cidr = var.vpc_cidr

  azs             = var.azs
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway     = true
  single_nat_gateway     = true
  enable_dns_hostnames   = true

  # Per-service micro-segmentation via NACLs
  manage_default_network_acl = true
  default_network_acl_ingress = [
    { rule_no = 100, action = "deny", from_port = 0, to_port = 0, protocol = "-1", cidr_block = "0.0.0.0/0" },
  ]
  default_network_acl_egress = [
    { rule_no = 100, action = "deny", from_port = 0, to_port = 0, protocol = "-1", cidr_block = "0.0.0.0/0" },
  ]

  tags = {
    Environment = var.environment
    Project     = "zero-trust-agentic-gateway"
  }
}

# Security groups implementing per-service micro-segmentation
resource "aws_security_group" "ai_gateway_sg" {
  name        = "${local.name_prefix}-ai-gateway-sg"
  description = "AI Gateway - only accepts from ALB, egress to internal services only"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    cidr_blocks     = ["0.0.0.0/0"]
    description     = "HTTPS from internet via ALB"
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = module.vpc.private_subnets_cidr_blocks
    description     = "Internal traffic only to private services"
  }

  tags = { Name = "${local.name_prefix}-ai-gateway-sg" }
}

resource "aws_security_group" "internal_service_sg" {
  name        = "${local.name_prefix}-internal-sg"
  description = "Internal services - only from AI Gateway SG"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8005
    protocol        = "tcp"
    security_groups = [aws_security_group.ai_gateway_sg.id]
    description     = "Internal service ports from AI Gateway"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name_prefix}-internal-sg" }
}

# ECS Fargate cluster
resource "aws_ecs_cluster" "zt_cluster" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = { Name = "${local.name_prefix}-cluster" }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "zt_logs" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 90
}

# IAM role for ECS tasks
resource "aws_iam_role" "ecs_task_role" {
  name = "${local.name_prefix}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# S3 bucket for immutable audit logs
resource "aws_s3_bucket" "audit_logs" {
  bucket = "${local.name_prefix}-audit-logs-${random_id.suffix.hex}"

  object_lock_enabled = true

  tags = { Name = "${local.name_prefix}-audit-logs" }
}

resource "aws_s3_bucket_versioning" "audit_logs_versioning" {
  bucket = aws_s3_bucket.audit_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "audit_logs_block" {
  bucket = aws_s3_bucket.audit_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "random_id" "suffix" {
  byte_length = 4
}

# CloudTrail for API monitoring
resource "aws_cloudtrail" "zt_trail" {
  name                          = "${local.name_prefix}-trail"
  s3_bucket_name                = aws_s3_bucket.audit_logs.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true

  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }

  tags = { Name = "${local.name_prefix}-trail" }
}

# VPC Flow Logs
resource "aws_flow_log" "vpc_flow_logs" {
  log_destination_type = "cloud-watch-logs"
  log_destination      = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type         = "ALL"
  vpc_id               = module.vpc.vpc_id

  iam_role_arn = aws_iam_role.flow_logs_role.arn

  tags = { Name = "${local.name_prefix}-vpc-flow-logs" }
}

resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  name              = "/vpc-flow-logs/${local.name_prefix}"
  retention_in_days = 30
}

resource "aws_iam_role" "flow_logs_role" {
  name = "${local.name_prefix}-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "vpc-flow-logs.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "flow_logs_policy" {
  name = "${local.name_prefix}-flow-logs-policy"
  role = aws_iam_role.flow_logs_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
      ]
      Resource = "*"
    }]
  })
}

# Outputs
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "audit_logs_bucket" {
  value = aws_s3_bucket.audit_logs.bucket
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.zt_cluster.name
}

output "cloudtrail_name" {
  value = aws_cloudtrail.zt_trail.name
}
