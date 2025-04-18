variable "aws_region" {
  description = "AWS region to deploy resources"
  default     = "us-west-2"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  default     = "myapp"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  default     = "dev"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  default     = "10.0.0.0/16"
  type        = string
}

variable "availability_zones" {
  description = "List of availability zones"
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
  type        = list(string)
}

variable "node_desired_capacity" {
  description = "Desired number of worker nodes"
  default     = 2
  type        = number
}

variable "node_max_capacity" {
  description = "Maximum number of worker nodes"
  default     = 5
  type        = number
}

variable "node_min_capacity" {
  description = "Minimum number of worker nodes"
  default     = 1
  type        = number
}

variable "node_instance_types" {
  description = "Instance types for worker nodes"
  default     = ["t3.medium"]
  type        = list(string)
}
EOL

cat > devops/terraform/outputs.tf << 'EOL'
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "eks_cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = aws_eks_cluster.main.endpoint
}

output "eks_cluster_security_group_ids" {
  description = "Security group ids attached to the cluster control plane"
  value       = aws_eks_cluster.main.vpc_config[0].security_group_ids
}

output "eks_cluster_name" {
  description = "Name of the EKS cluster"
  value       = aws_eks_cluster.main.name
}

output "eks_cluster_certificate_authority" {
  description = "Certificate authority data for the EKS cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
}