terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.72"
    }
  }
}

provider "aws" {
  region = "us-east-2"
}

resource "aws_iam_role" "onda" {
  name = "onda-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.onda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "onda" {
  function_name    = "onda"
  runtime          = "python3.14"
  handler          = "main.handler"
  architectures    = ["x86_64"]
  memory_size      = 256
  timeout          = 15
  role             = aws_iam_role.onda.arn
  filename         = "${path.module}/../docs/onda-lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../docs/onda-lambda.zip")

  depends_on = [aws_iam_role_policy_attachment.logs]
}

resource "aws_lambda_function_url" "onda" {
  function_name      = aws_lambda_function.onda.function_name
  authorization_type = "NONE"
}

output "url" {
  value = aws_lambda_function_url.onda.function_url
}
