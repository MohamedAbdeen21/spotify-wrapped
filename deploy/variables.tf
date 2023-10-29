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
