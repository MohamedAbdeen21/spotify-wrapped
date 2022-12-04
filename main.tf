provider "aws" {
  region = "me-south-1"
}

# environment variables 
variable "client_id" {
  description = "Spotify client id"
  type        = string
  sensitive   = true
}

variable "client_secret" {
  description = "spotify client secret"
  type        = string
  sensitive   = true
}

variable "email_password" {
  description = "email password for third-party apps"
  type        = string
  sensitive   = true
}

resource "aws_dynamodb_table" "tokens" {
  name           = "tokens_tf"
  billing_mode   = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "email"

  attribute {
    name = "email"
    type = "S"
  }

  tags = {
    Name        = "dynamo-table-1"
    Environment = "test"
  }
}

resource "aws_dynamodb_table" "listening_history" {
  name           = "listening_history_tf"
  billing_mode   = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "email"
  range_key      = "timestamp"

  attribute {
    name = "email"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  tags = {
    Name        = "dynamo-table-2"
    Environment = "test"
  }
}

module "lambda_load_listening_history" {
  source = "terraform-aws-modules/lambda/aws"

  function_name      = "load_listening_history_tf"
  handler            = "lambda_function.lambda_handler"
  runtime            = "python3.9"
  source_path        = "./load_listening_history"
  attach_policy_json = true
  policy_json = jsonencode(
    {
      Version = "2012-10-17",
      Statement = [
        {
          Effect : "Allow",
          Action : [
            "dynamodb:*",
            "lambda:*",
            "logs:*",
            "cloudwatch:*"
          ],
          Resource : ["*"]
        }
      ]
    }
  )
  timeout                                 = 200
  create_current_version_allowed_triggers = false
  allowed_triggers = {
    ScanAmiRule = {
      principal  = "events.amazonaws.com"
      source_arn = module.triggers.eventbridge_rule_arns["hourly_trigger"]
    }
  }
  memory_size = 1024
  environment_variables = {
    client_id     = var.client_id
    client_secret = var.client_secret
  }
}

data "archive_file" "go_package" {
  type        = "zip"
  source_file = "./report_to_SQS_go/main"
  output_path = "./report_to_SQS_go/main.zip"
}

resource "aws_sqs_queue" "emails_queue" {
  name                       = "sendEmails_tf"
  visibility_timeout_seconds = 120
}

module "lambda_report_to_sqs" {
  source                 = "terraform-aws-modules/lambda/aws"
  function_name          = "report_to_SQS_Go_tf"
  handler                = "main"
  runtime                = "go1.x"
  create_package         = false
  local_existing_package = "./report_to_SQS_go/main.zip"
  attach_policy_json     = true
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect : "Allow"
        Action : [
          "dynamodb:*",
          "lambda:*",
          "logs:*",
          "athena:*",
          "cloudwatch:*",
          "s3:*",
          "sqs:*"
        ]
        Resource : ["*"]
      }
    ]
  })
  create_async_event_config                 = true
  create_current_version_async_event_config = false
  create_current_version_allowed_triggers   = false
  allowed_triggers = {
    ScanAmiRule = {
      principal  = "events.amazonaws.com"
      source_arn = module.triggers.eventbridge_rule_arns["weekly_trigger"]
    }
  }
  destination_on_success = aws_sqs_queue.emails_queue.arn
  timeout                = 200
  memory_size            = 1024
}

module "lambda_send_emails" {
  source = "terraform-aws-modules/lambda/aws"

  function_name      = "send_emails_tf"
  handler            = "lambda_function.lambda_handler"
  runtime            = "python3.9"
  source_path        = "./send_emails"
  attach_policy_json = true
  policy_json = jsonencode(
    {
      Version = "2012-10-17",
      Statement = [
        {
          Effect : "Allow",
          Action : [
            "sqs:*",
            "lambda:*",
            "logs:*",
            "cloudwatch:*"
          ],
          Resource : ["*"]
        }
      ]
    }
  )
  timeout     = 120
  memory_size = 1024
  environment_variables = {
    email_password = var.email_password
    email_sender   = "wrapspotify@gmail.com"
  }
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  batch_size       = 1
  event_source_arn = aws_sqs_queue.emails_queue.arn
  enabled          = true
  function_name    = "send_emails_tf"
}

module "triggers" {
  source     = "terraform-aws-modules/eventbridge/aws"
  create_bus = false

  rules = {
    hourly_trigger = {
      description         = "Trigger load listening history"
      schedule_expression = "cron(58 * * * ? *)"
    }
    weekly_trigger = {
      description         = "Trigger report to SQS"
      schedule_expression = "cron(0 22 ? * FRI *)"
    }
  }

  targets = {
    hourly_trigger = [
      {
        name = "load_listening_history"
        arn  = module.lambda_load_listening_history.lambda_function_arn
      }
    ]
    weekly_trigger = [
      {
        name = "weekly_report"
        arn  = module.lambda_report_to_sqs.lambda_function_arn
      }
    ]
  }
}

// Need to create the DynamoDB-Athena connector from 
// console for now, use this S3 for output
// Update "athena_catalog" and "athena_database" constants
//  in `report_to_SQS_go/config.go` with the name of the
// connector and the database
resource "aws_s3_bucket" "query_spill" {
  bucket        = "spotify-wrapped-spill"
  force_destroy = true
}

// TODO: Registration lambda 