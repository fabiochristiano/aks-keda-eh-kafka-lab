output "acr" {
  value       = azurerm_container_registry.acr.name
  description = "Azure Container Registry Name"
}

output "eventhub_namespace" {
  value       = azurerm_eventhub_namespace.aks-keda-eh-kafka-lab.name
  description = "Event Hub Namespace"
}

output "managed_identity_id" {
  value       = azurerm_user_assigned_identity.aks-keda-eh-kafka-lab-app-identity.client_id
  description = "Managed Identity Client ID"
}