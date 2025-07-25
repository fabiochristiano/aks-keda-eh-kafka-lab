provider "azurerm" {
  features {}
  subscription_id = "<subscription_id>"
}

provider "kubernetes" {
    host = "${azurerm_kubernetes_cluster.aks.kube_config.0.host}"

    client_certificate     = "${base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_certificate)}"
    client_key             = "${base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_key)}"
    cluster_ca_certificate = "${base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.cluster_ca_certificate)}"
}

resource "random_string" "random-string" {
  length           = 6
  special          = false
}