resource "azurerm_virtual_network" "aks-keda-eh-kafka-lab" {
  name                = "aks-keda-eh-kafka-lab"
  resource_group_name = azurerm_resource_group.rg.name 
  location            = azurerm_resource_group.rg.location
  address_space       = ["10.254.0.0/16"]
}

resource "azurerm_subnet" "app" {
  name                 = "app"
  resource_group_name  = azurerm_resource_group.rg.name 
  virtual_network_name = azurerm_virtual_network.aks-keda-eh-kafka-lab.name
  address_prefixes     = ["10.254.0.0/22"]
}