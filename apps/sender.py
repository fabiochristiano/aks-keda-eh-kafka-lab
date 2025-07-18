#!/usr/bin/env python
"""
Event Hub Kafka Producer usando OAuth com Workload Identity
Baseado no exemplo oficial da Microsoft: 
https://github.com/Azure/azure-event-hubs-for-kafka/tree/master/tutorials/oauth/python
"""

import os
import random
import string
import time
import logging
import json
from azure.identity import DefaultAzureCredential
from confluent_kafka import Producer
from functools import partial

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variáveis de ambiente
EVENT_HUB_NAMESPACE = os.getenv('EVENT_HUB_NAMESPACE')
EVENT_HUB_NAME = os.getenv('EVENT_HUB_NAME')

logger.info(f"=== SENDER KAFKA OAUTH INICIADO ===")
logger.info(f"EVENT_HUB_NAMESPACE: {EVENT_HUB_NAMESPACE}")
logger.info(f"EVENT_HUB_NAME: {EVENT_HUB_NAME}")

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

def delivery_callback(err, msg):
    """Callback de entrega de mensagem"""
    if err:
        logger.error(f'Falha na entrega da mensagem: {err}')
    else:
        message_data = json.loads(msg.value().decode('utf-8'))
        logger.info(f'Mensagem entregue para {msg.topic()} [partition {msg.partition()}] @ offset {msg.offset()} - Order ID: {message_data["id"]}')

def send_message(producer, content):
    """Envia mensagem usando confluent-kafka producer"""
    try:
        message = {
            "id": content,
            "timestamp": time.time(),
            "message": f"Order {content}"
        }
        
        # Enviar mensagem
        producer.produce(
            topic=EVENT_HUB_NAME,
            value=json.dumps(message),
            callback=delivery_callback
        )
        
        logger.info(f"Mensagem produzida: {content}")
        
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}")

def main():
    """Função principal"""
    try:
        logger.info("Iniciando conexão com Event Hub via Kafka OAuth...")
        
        # Verificar variáveis de ambiente
        if not EVENT_HUB_NAMESPACE or not EVENT_HUB_NAME:
            logger.error("Variáveis de ambiente EVENT_HUB_NAMESPACE ou EVENT_HUB_NAME não definidas")
            return

        # Configuração do Producer Kafka com OAuth
        namespace_fqdn = f"{EVENT_HUB_NAMESPACE}.servicebus.windows.net"
        
        conf = {
            'bootstrap.servers': f'{namespace_fqdn}:9093',
            
            # Configuração OAuth obrigatória
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'OAUTHBEARER',
            
            # Callback OAuth usando partial para bind das credenciais
            'oauth_cb': partial(oauth_cb, credential, namespace_fqdn),
            
            # Configurações adicionais
            'api.version.request': True,
            'broker.version.fallback': '2.1.0',
            'request.timeout.ms': 30000,
            'retries': 3
        }
        
        logger.info(f"Conectando ao Event Hub: {namespace_fqdn}:9093")
        logger.info("Configuração OAuth configurada com DefaultAzureCredential")
        
        # Criar Producer
        producer = Producer(conf)
        logger.info("Producer Kafka OAuth criado com sucesso")
        
        # Gerar e enviar mensagens
        chars = string.digits
        
        while True:
            try:
                # Gerar conteúdo da mensagem
                content = ''.join(random.choice(chars) for _ in range(10))
                
                # Enviar mensagem
                send_message(producer, content)
                
                # Poll para processar callbacks de entrega
                producer.poll(0)
                
                # Aguardar um pouco entre mensagens
                time.sleep(0.1)
                
            except BufferError:
                logger.warning('Fila local do producer está cheia. Aguardando...')
                producer.poll(1)  # Aguardar 1 segundo
                
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem: {e}")
        
    except Exception as e:
        logger.error(f"Erro na aplicação principal: {e}")
        raise
    finally:
        try:
            if 'producer' in locals():
                producer.flush(30)  # Timeout de 30 segundos
                logger.info("Producer finalizado")
        except Exception as e:
            logger.error(f"Erro ao finalizar producer: {e}")

if __name__ == "__main__":
    main()