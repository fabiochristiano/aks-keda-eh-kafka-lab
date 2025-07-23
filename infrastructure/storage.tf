resource "azurerm_storage_account" "checkpoint" {
  name                     = "kedast${lower(random_string.random-string.result)}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  tags = {
    purpose = "keda-eventhub-checkpoints"
  }
}

resource "azurerm_storage_container" "checkpoints" {
  name                 = "eventhub-checkpoints"
  storage_account_id   = azurerm_storage_account.checkpoint.id
  container_access_type = "private"
}

# Grant the managed identity access to the storage account
resource "azurerm_role_assignment" "storage-blob-contributor" {
  scope                = azurerm_storage_account.checkpoint.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.aks-keda-eh-kafka-lab-app-identity.principal_id
}
