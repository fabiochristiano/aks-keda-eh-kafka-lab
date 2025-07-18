# AKS KEDA Event Hub Lab

Este laboratório demonstra o uso do **KEDA (Kubernetes Event Driven Autoscaling)** com **Azure Kubernetes Service (AKS)** e **Azure Event Hub**, focando em:

## 🎯 Objetivos do Laboratório

- **Event-driven autoscaling**: Implementar escalonamento automático baseado em eventos
- **Event Hub integration**: Usar Event Hub como trigger para escalonamento
- **Workload Identity**: Autenticação segura sem chaves/secrets
- **Scale-to-zero**: Demonstrar capacidade de escalar para zero réplicas

## 🏗️ Arquitetura do Lab

### Componentes principais:
- **AKS Cluster**: Kubernetes cluster com KEDA habilitado
- **Event Hub**: Hub "orders" para comunicação entre aplicações
- **Sender App**: Aplicação que envia mensagens para o Event Hub
- **Receiver App**: Aplicação que consome mensagens (escala automaticamente)
- **KEDA ScaledObject**: Configuração para escalonamento baseado no Event Hub
- **Workload Identity**: Autenticação segura para acesso ao Event Hub

### Fluxo de funcionamento:
1. **Sender** envia mensagens para o Event Hub "orders"
2. **KEDA** monitora o número de mensagens não processadas no Event Hub
3. **Receiver** escala automaticamente baseado na quantidade de mensagens
4. Quando não há mensagens, o **Receiver** escala para zero réplicas

## 🚀 Passo a Passo para Executar o Lab

### 1. Pré-requisitos

```bash
# Ferramentas necessárias
- Azure CLI
- Terraform
- kubectl
```

### 2. Deploy da Infraestrutura

```bash
# Clone o repositório e navegue para o diretório de infraestrutura
cd ./infrastructure

# Inicialize o Terraform
terraform init

# Planeje o deployment 
terraform plan 

# Execute o deployment
terraform apply 
```

**Outputs importantes do Terraform:**
- `acr`: Nome do Azure Container Registry
- `eventhub_namespace`: Nome do namespace Event Hub
- `managed_identity_id`: Client ID da identidade gerenciada

### 3. Configuração do kubectl

```bash
# Obtenha as credenciais do cluster AKS
az aks get-credentials --resource-group <resource_group_name> --name aks-keda-eh-kafka-lab

# Verifique a conexão
kubectl get nodes
```

### 4. Build e Push das Imagens

```bash
# Navegue para o diretório das aplicações
cd ./apps

# Faça build das imagens no ACR (substitua <acr_name> pelo output do terraform)
az acr build --registry <acr_name> --file Dockerfile-sender --image sender:v1 .
az acr build --registry <acr_name> --file Dockerfile-receiver --image receiver:v1 .
```

### 5. Atualize os Arquivos YAML

**Antes de aplicar os YAMLs, atualize as referências:**

**No arquivo `receiver.yaml` e `sender.yaml`:**
```yaml
# Substitua os parametros abaixo pelo output do Terraform:
image: <Azure Container Registry Name>.azurecr.io/receiver:v1
identityId: <Managed Identity Client ID>
eventHubNamespace: <Event Hub Namespace>

```

### 6. Deploy das Aplicações

```bash
# Aplique os manifests das aplicações
kubectl apply -f receiver.yaml
kubectl apply -f sender.yaml

# Verifique o deployment
kubectl get pods -n order
kubectl get scaledobject -n order
```

### 7. Teste o Escalonamento KEDA

```bash
# Monitore os pods em tempo real
kubectl get pods -n order -w

# Em outro terminal, monitore os logs do receiver
kubectl logs -l app=receiver -n order -f

# Em outro terminal, monitore os logs do sender
kubectl logs -l app=sender -n order -f
```

### 8. Escale o Sender para Gerar Mais Mensagens

```bash
# Escale o sender para gerar mais mensagens
kubectl scale deployment sender --replicas=3 -n order

# Observe o receiver escalar automaticamente
kubectl get pods -n order -w
```

### 9. Monitore o Event Hub

**No Azure Portal:**
- Navegue para: `Event Hubs > aks-keda-eh-kafka-lab-<random> > Event Hubs > orders`
- Observe a contagem de mensagens em tempo real
- Veja como o KEDA reage às mudanças no Event Hub

### 10. Teste Scale-to-Zero

```bash
# Pare o sender
kubectl scale deployment sender --replicas=0 -n order

# Observe o receiver escalar para zero após processar todas as mensagens
kubectl get pods -n order -w
```

## 📊 Comandos Úteis para Monitoramento

```bash
# Verificar o status do KEDA
kubectl get scaledobject -n order

# Verificar HPA criado pelo KEDA
kubectl get hpa -n order

# Verificar logs do KEDA
kubectl logs -l app=keda-operator -n keda-system

# Verificar detalhes do ScaledObject
kubectl describe scaledobject receiver -n order
```


## 🧹 Limpeza dos Recursos

```bash
# Remover as aplicações
kubectl delete -f receiver.yaml
kubectl delete -f sender.yaml

# Remover a infraestrutura
cd ./infrastructure
terraform destroy
```

## 📚 Documentação Relevante

- [KEDA Documentation](https://keda.sh/)
- [AKS KEDA Add-on](https://docs.microsoft.com/en-us/azure/aks/keda-about)
- [Azure Event Hub](https://docs.microsoft.com/en-us/azure/event-hubs/)
- [Azure Workload Identity](https://docs.microsoft.com/en-us/azure/aks/workload-identity-overview)