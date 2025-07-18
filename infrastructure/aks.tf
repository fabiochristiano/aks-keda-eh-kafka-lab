resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-keda-eh-kafka-lab"
  dns_prefix          = "aks-keda-eh-kafka-lab"
  resource_group_name = azurerm_resource_group.rg.name 
  location            = azurerm_resource_group.rg.location

  role_based_access_control_enabled = true
  oidc_issuer_enabled               = true
  workload_identity_enabled         = true
  
  workload_autoscaler_profile {
    keda_enabled = true
  }

  default_node_pool {
    name                        = "regular"
    temporary_name_for_rotation = "rotation"
    vm_size                     = "Standard_D2s_v5"
    auto_scaling_enabled        = true
    max_count                   = 8
    min_count                   = 2
    vnet_subnet_id              = azurerm_subnet.app.id
    zones                       = [ 1, 3 ]
  }

  network_profile {
    network_plugin      = "azure"
    service_cidr        = "172.29.100.0/24"
    dns_service_ip      = "172.29.100.10"
    network_plugin_mode = "overlay"
  }

  identity {
    type = "SystemAssigned"
  }

}

resource "azurerm_role_assignment" "aks-subnet" {
  scope                = azurerm_virtual_network.aks-keda-eh-kafka-lab.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_kubernetes_cluster.aks.identity.0.principal_id
}


