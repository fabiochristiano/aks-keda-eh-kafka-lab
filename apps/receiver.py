#!/usr/bin/env python
"""
Event Hub Kafka Consumer usando OAuth com Workload Identity
Baseado no exemplo oficial da Microsoft: 
https://github.com/Azure/azure-event-hubs-for-kafka/tree/master/tutorials/oauth/python
"""

import os
import time
import json
import logging
from azure.identity import DefaultAzureCredential
from confluent_kafka import Consumer
from functools import partial

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variáveis de ambiente
EVENT_HUB_NAMESPACE = os.getenv('EVENT_HUB_NAMESPACE')
EVENT_HUB_NAME = os.getenv('EVENT_HUB_NAME')
CONSUMER_GROUP = os.getenv('CONSUMER_GROUP')

logger.info(f"=== RECEIVER KAFKA OAUTH INICIADO ===")
logger.info(f"EVENT_HUB_NAMESPACE: {EVENT_HUB_NAMESPACE}")
logger.info(f"EVENT_HUB_NAME: {EVENT_HUB_NAME}")
logger.info(f"CONSUMER_GROUP: {CONSUMER_GROUP}")

# Credencial do Azure (Workload Identity)
credential = DefaultAzureCredential()

def oauth_cb(cred, namespace_fqdn, config):
    """
    Callback OAuth para confluent_kafka
    
    Args:
        cred: Azure credential object (DefaultAzureCredential)
        namespace_fqdn: Event Hub namespace FQDN (ex: mynamespace.servicebus.windows.net)
        config: confluent_kafka passa 'sasl.oauthbearer.config' como parâmetro config
    
    Returns:
        tuple: (access_token, expiration_timestamp)
    """
    try:
        logger.info(f"Obtendo token OAuth via callback para namespace: {namespace_fqdn}")
        # Usar o escopo específico do namespace para Event Hub
        scope = f"https://{namespace_fqdn}/.default"
        access_token = cred.get_token(scope)
        logger.info(f"Token OAuth obtido com sucesso para escopo: {scope}")
        
        # Retornar token e timestamp de expiração
        return access_token.token, access_token.expires_on
    except Exception as e:
        logger.error(f"Erro no callback OAuth: {e}")
        raise

def main():
    """Função principal"""
    try:
        logger.info("Iniciando conexão com Event Hub via Kafka OAuth...")
        
        # Verificar variáveis de ambiente
        if not EVENT_HUB_NAMESPACE or not EVENT_HUB_NAME or not CONSUMER_GROUP:
            logger.error("Variáveis de ambiente EVENT_HUB_NAMESPACE, EVENT_HUB_NAME ou CONSUMER_GROUP não definidas")
            return

        # Configuração do Consumer Kafka com OAuth
        namespace_fqdn = f"{EVENT_HUB_NAMESPACE}.servicebus.windows.net"
        
        conf = {
            'bootstrap.servers': f'{namespace_fqdn}:9093',
            
            # Configuração OAuth obrigatória
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'OAUTHBEARER',
            
            # Callback OAuth usando partial para bind das credenciais
            'oauth_cb': partial(oauth_cb, credential, namespace_fqdn),
            
            # Configurações do Consumer
            'group.id': CONSUMER_GROUP,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            
            # Configurações adicionais
            'api.version.request': True,
            'broker.version.fallback': '2.1.0',
            'request.timeout.ms': 30000,
            'retries': 3
        }
        
        logger.info(f"Conectando ao Event Hub: {namespace_fqdn}:9093")
        logger.info("Configuração OAuth configurada com DefaultAzureCredential")
        
        # Criar Consumer
        consumer = Consumer(conf)
        logger.info("Consumer Kafka OAuth criado com sucesso")
        
        # Subscrever ao tópico
        consumer.subscribe([EVENT_HUB_NAME])
        logger.info(f"Subscrito ao tópico: {EVENT_HUB_NAME}")
        logger.info("Aguardando mensagens...")
        
        while True:
            try:
                # Poll para mensagens (timeout de 1 segundo)
                msg = consumer.poll(1.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    logger.error(f"Erro do consumer: {msg.error()}")
                    continue
                
                # Processar mensagem recebida
                try:
                    message_data = json.loads(msg.value().decode('utf-8'))
                    logger.info(f'Mensagem recebida de {msg.topic()} [partition {msg.partition()}] @ offset {msg.offset()} - Order ID: {message_data["id"]}')
                except json.JSONDecodeError:
                    logger.info(f'Mensagem recebida de {msg.topic()} [partition {msg.partition()}] @ offset {msg.offset()} - Conteúdo: {msg.value().decode("utf-8")}')
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {e}")
        
    except Exception as e:
        logger.error(f"Erro na aplicação principal: {e}")
        raise
    finally:
        try:
            if 'consumer' in locals():
                consumer.close()
                logger.info("Consumer finalizado")
        except Exception as e:
            logger.error(f"Erro ao finalizar consumer: {e}")

if __name__ == "__main__":
    main()