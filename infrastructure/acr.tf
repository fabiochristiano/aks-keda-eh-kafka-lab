resource "azurerm_container_registry" "acr" {
  name                          = "akskedaehlab${random_string.random-string.result}"
  resource_group_name           = azurerm_resource_group.rg.name 
  location                      = azurerm_resource_group.rg.location
  sku                           = "Standard"
  public_network_access_enabled = true
}

resource "azurerm_role_assignment" "aks-acr" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity.0.object_id
}