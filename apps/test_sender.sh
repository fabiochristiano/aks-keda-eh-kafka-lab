#xport EVENT_HUB_NAMESPACE="aks-keda-eh-lab-9zbdqD" && export EVENT_HUB_NAME="orders" && timeout 10 python sender.py


#!/bin/bash

# Script para testar Event Hub Kafka OAuth localmente
# Certifique-se de estar logado no Azure CLI: az login

echo "=== Teste Local Event Hub Kafka OAuth - Sender ==="

# Verificar se está logado no Azure
echo "Verificando autenticação Azure..."
if ! az account show &> /dev/null; then
    echo "❌ Não está logado no Azure. Execute os seguintes comandos:"
    echo "   az login"
    echo "   az account set --subscription <your-subscription-id>"
    exit 1
fi

echo "✅ Autenticado no Azure"

# Verificar se tem acesso ao Event Hub
echo "Verificando acesso ao Event Hub..."
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "Subscription ID: $SUBSCRIPTION_ID"

# Tentar listar Event Hub namespaces para verificar permissões
if ! az eventhubs namespace list --query "[].name" -o tsv &> /dev/null; then
    echo "⚠️  Aviso: Pode não ter permissões para listar Event Hub namespaces"
    echo "   Verifique se tem as roles necessárias:"
    echo "   - Azure Event Hubs Data Sender"
    echo "   - Azure Event Hubs Data Receiver (se for testar consumer)"
else
    echo "✅ Permissões do Azure CLI verificadas"
fi

# Definir variáveis de ambiente
export EVENT_HUB_NAMESPACE="aks-keda-eh-lab-9zbdqD"
export EVENT_HUB_NAME="orders"

echo "Variáveis de ambiente configuradas:"
echo "  EVENT_HUB_NAMESPACE=$EVENT_HUB_NAMESPACE"
echo "  EVENT_HUB_NAME=$EVENT_HUB_NAME"

# Instalar dependências
echo ""
echo "Instalando dependências..."
pip install -r requirements.txt

# Testar sender
echo ""
echo "=== Testando Sender Kafka OAuth ==="
echo "IMPORTANTE: Se você receber erro de autenticação, execute:"
echo "  1. az login"
echo "  2. az account set --subscription <your-subscription-id>"
echo "  3. Verifique se tem as roles necessárias no Event Hub:"
echo "     - Azure Event Hubs Data Sender"
echo "     - Azure Event Hubs Data Receiver"
echo ""
echo "Executando sender.py..."
echo "Pressione Ctrl+C para parar"
python sender.py
