# Workload Identity no AKS com KEDA e Event Hub

Este documento explica como o Workload Identity está implementado neste projeto, permitindo que os aplicativos no AKS acessem o Azure Event Hub de forma segura sem gerenciamento de secrets.

## O que é Workload Identity?

Workload Identity é uma forma moderna e segura de permitir que pods Kubernetes autentiquem-se em recursos Azure sem precisar armazenar credenciais ou chaves. Ela estabelece uma relação de confiança entre o Azure AD e o Kubernetes, permitindo que pods obtenham tokens de acesso de forma transparente.

## Componentes principais do Workload Identity

### 1. User Assigned Managed Identity (no Azure)

```terraform
resource "azurerm_user_assigned_identity" "aks-keda-eh-kafka-lab-app-identity" {
  name                = "aks-keda-eh-kafka-lab-app-identity"
  resource_group_name = azurerm_resource_group.rg.name 
  location            = azurerm_resource_group.rg.location
}
```

- Este recurso cria uma identidade gerenciada no Azure
- Esta identidade recebe permissões específicas (via role assignments) para acessar o Event Hub
- É o "quem" no lado do Azure que tem permissão para acessar recursos

### 2. Kubernetes Service Account (no AKS)

```terraform
resource "kubernetes_service_account" "aks-keda-eh-kafka-lab-app-sa" {
  metadata {
    name = "aks-keda-eh-kafka-lab-app-sa"
    namespace = kubernetes_namespace.order.metadata.0.name
    annotations = {
         "azure.workload.identity/client-id" = azurerm_user_assigned_identity.aks-keda-eh-kafka-lab-app-identity.client_id
    }
  }
}
```

- Cria uma conta de serviço no Kubernetes
- A annotation `azure.workload.identity/client-id` associa esta conta com a identidade Azure
- Pods que usam esta service account podem autenticar-se nos recursos Azure
- É o "quem" no lado do Kubernetes que precisa de acesso aos recursos Azure

### 3. Federated Identity Credential (a ponte)

```terraform
resource "azurerm_federated_identity_credential" "aks-keda-eh-kafka-lab-app-federated" {
  name                = "aks-keda-eh-kafka-lab-app-federated"
  resource_group_name = azurerm_resource_group.rg.name 
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.aks.oidc_issuer_url
  parent_id           = azurerm_user_assigned_identity.aks-keda-eh-kafka-lab-app-identity.id
  subject             = "system:serviceaccount:${kubernetes_namespace.order.metadata.0.name}:${kubernetes_service_account.aks-keda-eh-kafka-lab-app-sa.metadata.0.name}"
}
```

- Cria a "ponte" de confiança entre a identidade Azure e a Service Account Kubernetes
- Define quem (`subject`) pode obter tokens para esta identidade
- Define quem é o emissor de tokens de confiança (`issuer`)
- É o contrato que permite ao Azure AD confiar em tokens emitidos pelo AKS

### 4. Role Assignment (permissões)

```terraform
resource "azurerm_role_assignment" "aks-keda-eh-kafka-lab-app-data-owner" {
  scope                = azurerm_eventhub_namespace.aks-keda-eh-kafka-lab.id
  role_definition_name = "Azure Event Hubs Data Owner"
  principal_id         = azurerm_user_assigned_identity.aks-keda-eh-kafka-lab-app-identity.principal_id
}
```

- Atribui a permissão "Azure Event Hubs Data Owner" para a identidade gerenciada
- Define o escopo dessa permissão (todo o namespace do Event Hub)
- Define "o que" a identidade pode fazer (enviar/receber mensagens)

## Como funciona o fluxo completo

1. O AKS é configurado com `workload_identity_enabled = true`
2. O pod usa a service account `aks-keda-eh-kafka-lab-app-sa` na configuração YAML:
   ```yaml
   spec:
     serviceAccountName: aks-keda-eh-kafka-lab-app-sa
   ```
3. Quando o pod precisa acessar o Event Hub:
   - O SDK Azure dentro do pod usa o DefaultAzureCredential 
   - Este detecta o ambiente Kubernetes com Workload Identity
   - Solicita um token ao serviço de token projetado no pod
   - O token é trocado pela Azure AD por um token para acessar o Azure Event Hub
   - O Event Hub valida o token e permite o acesso

## Componente KEDA (escalonamento)

Para o KEDA também, foi criada uma configuração semelhante:

```terraform
resource "azurerm_federated_identity_credential" "aks-keda-eh-kafka-lab-operator" {
  name                = "aks-keda-eh-kafka-lab-operator"
  resource_group_name = azurerm_resource_group.rg.name 
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.aks.oidc_issuer_url
  parent_id           = azurerm_user_assigned_identity.aks-keda-eh-kafka-lab-app-identity.id
  subject             = "system:serviceaccount:kube-system:keda-operator"
}
```

- Esta configuração permite que o operador KEDA autentique-se no Azure Event Hub
- Assim o KEDA pode consultar o Event Hub para determinar quando escalar os pods
- O KEDA irá escalar automaticamente os pods com base na quantidade de mensagens não processadas

## Benefícios desta abordagem

1. **Segurança**: Nenhuma credencial é armazenada nos pods ou código
2. **Gerenciamento**: Rotação automática de certificados e chaves
3. **Granularidade**: Permissões específicas para recursos específicos
4. **Auditoria**: Ações rastreáveis até o Kubernetes service account
5. **Zero-Trust**: Segue os princípios modernos de segurança zero-trust

## Como é utilizado no código da aplicação

Em aplicações Python, você pode usar o DefaultAzureCredential, que automaticamente detecta e usa o Workload Identity quando disponível:

```python
# Python
from azure.identity import DefaultAzureCredential
from azure.eventhub import EventHubProducerClient, EventHubConsumerClient

credential = DefaultAzureCredential()

# Para enviar mensagens
producer = EventHubProducerClient(
    fully_qualified_namespace=f"{eventhub_namespace}.servicebus.windows.net",
    eventhub_name="orders",
    credential=credential
)

# Para receber mensagens
consumer = EventHubConsumerClient(
    fully_qualified_namespace=f"{eventhub_namespace}.servicebus.windows.net",
    eventhub_name="orders",
    consumer_group="orders-consumer",
    credential=credential
)
```

```csharp
// C#
using Azure.Identity;
using Azure.Messaging.EventHubs;
using Azure.Messaging.EventHubs.Producer;
using Azure.Messaging.EventHubs.Consumer;

var credential = new DefaultAzureCredential();

// Para enviar mensagens
var producer = new EventHubProducerClient(
    $"{eventHubNamespace}.servicebus.windows.net", 
    "orders",
    credential);

// Para receber mensagens
var consumer = new EventHubConsumerClient(
    "orders-consumer",
    $"{eventHubNamespace}.servicebus.windows.net",
    "orders", 
    credential);
```

Esta é uma implementação moderna de segurança que segue o princípio de menor privilégio e elimina a necessidade de gerenciar secrets para autenticação.
