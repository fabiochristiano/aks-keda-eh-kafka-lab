resource "kubernetes_namespace" "order" {
  metadata {
    name = "order"
  }
}

resource "azurerm_user_assigned_identity" "aks-keda-eh-kafka-lab-app-identity" {
  name                = "aks-keda-eh-kafka-lab-app-identity"
  resource_group_name = azurerm_resource_group.rg.name 
  location            = azurerm_resource_group.rg.location
}

resource "kubernetes_service_account" "aks-keda-eh-kafka-lab-app-sa" {
  metadata {
    name = "aks-keda-eh-kafka-lab-app-sa"
    namespace = kubernetes_namespace.order.metadata.0.name
    annotations = {
         "azure.workload.identity/client-id" = azurerm_user_assigned_identity.aks-keda-eh-kafka-lab-app-identity.client_id
    }
  }
}

resource "azurerm_federated_identity_credential" "aks-keda-eh-kafka-lab-app-federated" {
  name                = "aks-keda-eh-kafka-lab-app-federated"
  resource_group_name = azurerm_resource_group.rg.name 
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.aks.oidc_issuer_url
  parent_id           = azurerm_user_assigned_identity.aks-keda-eh-kafka-lab-app-identity.id
  subject             = "system:serviceaccount:${kubernetes_namespace.order.metadata.0.name}:${kubernetes_service_account.aks-keda-eh-kafka-lab-app-sa.metadata.0.name}"
}

resource "azurerm_federated_identity_credential" "aks-keda-eh-kafka-lab-operator" {
  name                = "aks-keda-eh-kafka-lab-operator"
  resource_group_name = azurerm_resource_group.rg.name 
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.aks.oidc_issuer_url
  parent_id           = azurerm_user_assigned_identity.aks-keda-eh-kafka-lab-app-identity.id
  subject             = "system:serviceaccount:kube-system:keda-operator"
}