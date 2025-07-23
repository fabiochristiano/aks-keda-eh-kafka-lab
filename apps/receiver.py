#!/usr/bin/env python
"""
Event Hub Kafka Consumer usando OAuth com Workload Identity
Baseado no exemplo oficial da Microsoft: 
https://github.com/Azure/azure-event-hubs-for-kafka/tree/master/tutorials/oauth/python
"""

import os
import sys
import time
import json
import logging
from azure.identity import DefaultAzureCredential
from confluent_kafka import Consumer
from functools import partial

# Configurar logging com nível DEBUG
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Habilitar logging debug para confluent_kafka
logging.getLogger('confluent_kafka').setLevel(logging.DEBUG)

# Variáveis de ambiente
EVENT_HUB_NAMESPACE = os.getenv('EVENT_HUB_NAMESPACE')
EVENT_HUB_NAME = os.getenv('EVENT_HUB_NAME')
CONSUMER_GROUP = os.getenv('CONSUMER_GROUP')

logger.info(f"=== RECEIVER KAFKA OAUTH INICIADO ===")
logger.info(f"EVENT_HUB_NAMESPACE: {EVENT_HUB_NAMESPACE}")
logger.info(f"EVENT_HUB_NAME: {EVENT_HUB_NAME}")
logger.info(f"CONSUMER_GROUP: {CONSUMER_GROUP}")
logger.debug(f"Python version: {sys.version}")
logger.debug(f"Confluent Kafka version disponível")

# Credencial do Azure (Workload Identity)
logger.debug("Inicializando DefaultAzureCredential...")
start_time = time.time()
credential = DefaultAzureCredential()
logger.debug(f"DefaultAzureCredential inicializado em {time.time() - start_time:.2f}s")

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
        logger.debug(f"=== INICIO CALLBACK OAUTH ===")
        logger.debug(f"Obtendo token OAuth via callback para namespace: {namespace_fqdn}")
        logger.debug(f"Config recebido: {config}")
        
        # Medir tempo de obtenção do token
        token_start = time.time()
        
        # Usar o escopo específico do namespace para Event Hub
        scope = f"https://{namespace_fqdn}/.default"
        logger.debug(f"Solicitando token para escopo: {scope}")
        
        access_token = cred.get_token(scope)
        token_duration = time.time() - token_start
        
        logger.debug(f"Token OAuth obtido em {token_duration:.2f}s para escopo: {scope}")
        logger.debug(f"Token expira em: {access_token.expires_on} (timestamp)")
        logger.debug(f"=== FIM CALLBACK OAUTH ===")
        
        # Retornar token e timestamp de expiração
        return access_token.token, access_token.expires_on
    except Exception as e:
        logger.error(f"Erro no callback OAuth: {e}")
        raise

def main():
    """Função principal"""
    try:
        logger.info("=== INICIANDO APLICAÇÃO RECEIVER ===")
        logger.debug("Iniciando conexão com Event Hub via Kafka OAuth...")
        
        # Verificar variáveis de ambiente
        logger.debug("Verificando variáveis de ambiente...")
        if not EVENT_HUB_NAMESPACE or not EVENT_HUB_NAME or not CONSUMER_GROUP:
            logger.error("Variáveis de ambiente EVENT_HUB_NAMESPACE, EVENT_HUB_NAME ou CONSUMER_GROUP não definidas")
            return

        logger.debug("Todas as variáveis de ambiente estão definidas")
        
        # Teste de conectividade DNS
        namespace_fqdn = f"{EVENT_HUB_NAMESPACE}.servicebus.windows.net"
        logger.debug(f"FQDN do Event Hub: {namespace_fqdn}")
        
        # Teste inicial de credencial
        logger.debug("Testando credencial Azure antes de configurar consumer...")
        try:
            test_start = time.time()
            scope = f"https://{namespace_fqdn}/.default"
            test_token = credential.get_token(scope)
            test_duration = time.time() - test_start
            logger.debug(f"Teste de credencial bem-sucedido em {test_duration:.2f}s")
        except Exception as e:
            logger.error(f"Falha no teste de credencial: {e}")
            raise
        
        # Configuração do Consumer Kafka com OAuth
        logger.debug("=== CONFIGURANDO CONSUMER KAFKA ===")
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
            
            # Configurações adicionais para debug
            'api.version.request': True,
            'broker.version.fallback': '2.1.0',
            'request.timeout.ms': 30000,
            'retries': 3,
            'debug': 'broker,topic,metadata,consumer,cgrp,protocol'  # Debug detalhado
        }
        
        logger.debug(f"Configuração do consumer:")
        for key, value in conf.items():
            if key != 'oauth_cb':  # Não logar o callback function
                logger.debug(f"  {key}: {value}")
        
        logger.info(f"Conectando ao Event Hub: {namespace_fqdn}:9093")
        logger.debug("Configuração OAuth configurada com DefaultAzureCredential")
        
        # Criar Consumer
        logger.debug("=== CRIANDO CONSUMER KAFKA ===")
        consumer_start = time.time()
        consumer = Consumer(conf)
        consumer_duration = time.time() - consumer_start
        logger.info(f"Consumer Kafka OAuth criado em {consumer_duration:.2f}s")
        
        # Subscrever ao tópico
        logger.debug("=== FAZENDO SUBSCRIBE AO TÓPICO ===")
        subscribe_start = time.time()
        consumer.subscribe([EVENT_HUB_NAME])
        subscribe_duration = time.time() - subscribe_start
        logger.info(f"Subscrito ao tópico: {EVENT_HUB_NAME} em {subscribe_duration:.2f}s")
        
        # Aguardar assignment de partições
        logger.debug("=== AGUARDANDO ASSIGNMENT DE PARTIÇÕES ===")
        assignment_start = time.time()
        assignment_timeout = 30  # 30 segundos timeout
        
        while True:
            assignment = consumer.assignment()
            if assignment:
                assignment_duration = time.time() - assignment_start
                logger.info(f"Partições assignadas em {assignment_duration:.2f}s: {assignment}")
                break
            
            if time.time() - assignment_start > assignment_timeout:
                logger.warning(f"Timeout de {assignment_timeout}s aguardando assignment de partições")
                break
                
            logger.debug("Aguardando assignment de partições...")
            time.sleep(1)
        
        logger.info("=== INICIANDO LOOP DE CONSUMO ===")
        logger.info("Aguardando mensagens...")
        
        poll_count = 0
        last_log_time = time.time()
        
        while True:
            try:
                poll_count += 1
                
                # Log periódico de status (a cada 30 segundos)
                current_time = time.time()
                if current_time - last_log_time >= 30:
                    logger.debug(f"Status: {poll_count} polls realizados, aguardando mensagens...")
                    
                    # Verificar assignment atual
                    current_assignment = consumer.assignment()
                    logger.debug(f"Assignment atual: {current_assignment}")
                    
                    # Verificar posições
                    if current_assignment:
                        for tp in current_assignment:
                            try:
                                position = consumer.position([tp])
                                committed = consumer.committed([tp])
                                logger.debug(f"Partição {tp.partition}: position={position}, committed={committed}")
                            except Exception as e:
                                logger.debug(f"Erro ao obter posição da partição {tp.partition}: {e}")
                    
                    last_log_time = current_time
                
                # Poll para mensagens (timeout de 1 segundo)
                poll_start = time.time()
                msg = consumer.poll(1.0)
                poll_duration = time.time() - poll_start
                
                if msg is None:
                    if poll_count <= 10 or poll_count % 100 == 0:  # Log apenas primeiros polls e depois esporadicamente
                        logger.debug(f"Poll #{poll_count}: Nenhuma mensagem (tempo: {poll_duration:.3f}s)")
                    continue
                    
                if msg.error():
                    logger.error(f"Erro do consumer: {msg.error()}")
                    continue
                
                # Processar mensagem recebida
                logger.debug(f"=== MENSAGEM RECEBIDA (Poll #{poll_count}) ===")
                try:
                    message_data = json.loads(msg.value().decode('utf-8'))
                    logger.info(f'Mensagem recebida de {msg.topic()} [partition {msg.partition()}] @ offset {msg.offset()} - Order ID: {message_data["id"]}')
                    logger.debug(f'Dados completos da mensagem: {message_data}')
                except json.JSONDecodeError:
                    message_content = msg.value().decode('utf-8')
                    logger.info(f'Mensagem recebida de {msg.topic()} [partition {msg.partition()}] @ offset {msg.offset()} - Conteúdo: {message_content}')
                    logger.debug(f'Mensagem raw: {msg.value()}')
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Erro ao processar mensagem (Poll #{poll_count}): {e}")
                logger.debug(f"Detalhes do erro: {type(e).__name__}: {str(e)}")
        
    except Exception as e:
        logger.error(f"Erro na aplicação principal: {e}")
        logger.debug(f"Detalhes do erro principal: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        raise
    finally:
        try:
            if 'consumer' in locals():
                logger.debug("Fechando consumer...")
                consumer.close()
                logger.info("Consumer finalizado")
        except Exception as e:
            logger.error(f"Erro ao finalizar consumer: {e}")

if __name__ == "__main__":
    main()