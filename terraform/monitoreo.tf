# Si la app responde 5 o más errores en 5 minutos, CloudWatch lo detecta y SNS avisa por correo.

resource "aws_sns_topic" "alertas" {
  name = "onda-alertas"
}

resource "aws_sns_topic_subscription" "correo" {
  topic_arn = aws_sns_topic.alertas.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "errores" {
  alarm_name          = "onda-errores"
  alarm_description   = "5 o más respuestas 5xx en 5 min: Deezer caído o error del servidor"
  namespace           = "AWS/Lambda"
  metric_name         = "Url5xxCount"
  dimensions          = { FunctionName = aws_lambda_function.onda.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alertas.arn] # correo cuando falla
  ok_actions          = [aws_sns_topic.alertas.arn] # correo cuando se recupera
}
