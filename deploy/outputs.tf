output "lambda_invoke_url" {
  value       = module.registration_api_tf.lambda_function_url
  description = "The URL to register for the service"
  depends_on  = [module.registration_api_tf]
}

