output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "audit_logs_bucket" {
  description = "S3 bucket name for immutable audit logs"
  value       = aws_s3_bucket.audit_logs.bucket
}

output "ecs_cluster_name" {
  description = "ECS Fargate cluster name"
  value       = aws_ecs_cluster.zt_cluster.name
}

output "cloudtrail_name" {
  description = "CloudTrail trail name"
  value       = aws_cloudtrail.zt_trail.name
}

output "ai_gateway_sg_id" {
  description = "AI Gateway security group ID"
  value       = aws_security_group.ai_gateway_sg.id
}

output "internal_service_sg_id" {
  description = "Internal services security group ID"
  value       = aws_security_group.internal_service_sg.id
}
