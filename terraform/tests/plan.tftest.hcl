# Test sans compte AWS : les réponses d'AWS sont simulées ("mock").
# Lancer : terraform -chdir=terraform test
mock_provider "aws" {
  mock_data "aws_ec2_instance_type_offerings" { defaults = { locations = ["us-east-1a", "us-east-1b"] } }
  mock_data "aws_subnets" { defaults = { ids = ["subnet-b", "subnet-a"] } }
  mock_data "aws_ami" { defaults = { id = "ami-123" } }
  mock_data "aws_vpc" { defaults = { id = "vpc-1" } }
  mock_resource "aws_eip" { defaults = { public_ip = "203.0.113.7" } }
}
mock_provider "http" {
  mock_data "http" { defaults = { response_body = "198.51.100.9\n" } }
}
variables { ssh_public_key_path = "./tests/key.pub" }
run "infrastructure" {
  command = apply
  assert {
    condition     = tolist(output.allowed_cidrs) == tolist(["198.51.100.9/32"])
    error_message = "cidr"
  }
  assert {
    condition     = aws_instance.node.subnet_id == "subnet-a"
    error_message = "subnet"
  }
  assert {
    condition     = strcontains(aws_instance.node.user_data, "PUBLIC_IP=\"203.0.113.7\"")
    error_message = "ip"
  }
  assert {
    condition     = output.ssh_command == "ssh -i ./tests/key ubuntu@203.0.113.7"
    error_message = "ssh"
  }
}
