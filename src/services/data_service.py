"""
Serviço integrado de dados que combina coleta, processamento e armazenamento
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import threading
import time

from src.collectors.main_collector import MainCollector
from src.processors.data_processor import DataProcessor
from src.storage.storage_manager import StorageManager

class DataService:
    """Serviço principal que coordena coleta, processamento e armazenamento"""
    
    def __init__(self, app=None, config: Optional[Dict] = None):
        self.app = app
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Componentes principais
        self.collector = None
        self.processor = None
        self.storage = None
        
        # Estado do serviço
        self.is_running = False
        self.last_collection = None
        self.collection_thread = None
        
        # Configurações
        self.auto_collection_interval = self.config.get('auto_collection_interval', 3600)  # 1 hora
        self.enable_auto_collection = self.config.get('enable_auto_collection', False)
        self.max_retries = self.config.get('max_retries', 3)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa o serviço com a aplicação Flask"""
        self.app = app
        
        # Inicializa componentes
        collector_config = self.config.get('collector', {})
        self.collector = MainCollector(collector_config)
        
        self.processor = DataProcessor()
        
        self.storage = StorageManager(app)
        
        self.logger.info("DataService inicializado com sucesso")
    
    def collect_and_process(self, save_to_db: bool = True, use_cache: bool = True) -> Dict[str, Any]:
        """
        Executa coleta completa com processamento e armazenamento
        
        Args:
            save_to_db: Se deve salvar no banco de dados
            use_cache: Se deve usar cache para otimização
            
        Returns:
            Resultados da operação completa
        """
        operation_start = time.time()
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'collection_results': None,
            'processed_data': None,
            'storage_id': None,
            'duration_seconds': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            self.logger.info("Iniciando coleta e processamento completo")
            
            # Verifica cache se habilitado
            if use_cache:
                cache_key = f"full_collection_{datetime.now().strftime('%Y%m%d_%H')}"
                cached_result = self.storage.cache_get(cache_key)
                if cached_result:
                    self.logger.info("Dados encontrados no cache")
                    result.update(cached_result)
                    result['from_cache'] = True
                    return result
            
            # Atualiza status das APIs antes da coleta
            self._update_apis_status()
            
            # Executa coleta
            self.logger.info("Executando coleta de dados")
            collection_results = self.collector.collect_all_data()
            result['collection_results'] = collection_results
            
            if not collection_results.get('summary', {}).get('successful', 0):
                result['errors'].append("Nenhuma fonte de dados foi coletada com sucesso")
                return result
            
            # Processa dados coletados
            self.logger.info("Processando dados coletados")
            processed_data = self.processor.process_collection_results(collection_results)
            result['processed_data'] = processed_data
            
            # Armazena no banco se solicitado
            if save_to_db:
                self.logger.info("Armazenando dados no banco")
                storage_id = self.storage.store_collection_results(collection_results, processed_data)
                result['storage_id'] = storage_id
                
                # Log da operação
                self.storage.log('INFO', 'data_service', 
                               f"Coleta e processamento concluídos. ID: {storage_id}",
                               {'collection_summary': collection_results.get('summary')})
            
            # Armazena no cache se habilitado
            if use_cache:
                cache_ttl = timedelta(hours=1)
                cache_data = {
                    'timestamp': result['timestamp'],
                    'collection_results': collection_results,
                    'processed_data': processed_data,
                    'storage_id': result['storage_id'],
                    'from_cache': False
                }
                self.storage.cache_set(cache_key, cache_data, 'full_collection', cache_ttl)
            
            result['success'] = True
            self.last_collection = datetime.now()
            
            # Calcula métricas de qualidade
            quality_metrics = processed_data.get('quality_metrics', {})
            if quality_metrics.get('total_validation_errors', 0) > 0:
                result['warnings'].append(f"Encontrados {quality_metrics['total_validation_errors']} erros de validação")
            
            self.logger.info(f"Coleta e processamento concluídos com sucesso. Taxa de sucesso: {quality_metrics.get('processing_success_rate', 0):.1f}%")
            
        except Exception as e:
            self.logger.error(f"Erro durante coleta e processamento: {str(e)}")
            result['errors'].append(f"Erro geral: {str(e)}")
            
            # Log do erro
            if self.storage:
                self.storage.log('ERROR', 'data_service', 
                               f"Erro durante coleta e processamento: {str(e)}")
        
        finally:
            result['duration_seconds'] = round(time.time() - operation_start, 2)
        
        return result
    
    def get_latest_data_summary(self) -> Dict[str, Any]:
        """Obtém resumo dos dados mais recentes"""
        try:
            # Busca última coleta bem-sucedida
            collection_history = self.storage.get_collection_history(limit=1)
            if not collection_history:
                return {'error': 'Nenhuma coleta encontrada'}
            
            latest_collection = collection_history[0]
            
            # Busca dados mais recentes por tipo
            data_types = [
                'ibge_municipio_info', 'ibge_populacao', 'ibge_pib_municipal',
                'bcb_ipca_12m', 'bcb_selic_atual', 'bcb_dolar_30d',
                'transparencia_convenios_municipio', 'dados_gov_organizacoes'
            ]
            
            latest_data = {}
            for data_type in data_types:
                data = self.storage.get_latest_data(data_type, limit=1)
                if data:
                    latest_data[data_type] = data[0]
            
            # Status das APIs
            apis_status = self.storage.get_apis_status()
            
            summary = {
                'timestamp': datetime.now().isoformat(),
                'last_collection': latest_collection,
                'latest_data_count': len(latest_data),
                'apis_status': apis_status,
                'service_status': {
                    'is_running': self.is_running,
                    'auto_collection_enabled': self.enable_auto_collection,
                    'last_collection_time': self.last_collection.isoformat() if self.last_collection else None
                }
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Erro ao obter resumo dos dados: {str(e)}")
            return {'error': str(e)}
    
    def get_data_by_type(self, data_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém dados por tipo específico
        
        Args:
            data_type: Tipo de dados
            limit: Número máximo de registros
            
        Returns:
            Lista de dados
        """
        try:
            return self.storage.get_latest_data(data_type, limit)
        except Exception as e:
            self.logger.error(f"Erro ao buscar dados do tipo {data_type}: {str(e)}")
            return []
    
    def get_collection_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtém histórico de coletas"""
        try:
            return self.storage.get_collection_history(limit)
        except Exception as e:
            self.logger.error(f"Erro ao buscar histórico: {str(e)}")
            return []
    
    def get_apis_status(self) -> List[Dict[str, Any]]:
        """Obtém status atual das APIs"""
        try:
            return self.storage.get_apis_status()
        except Exception as e:
            self.logger.error(f"Erro ao buscar status das APIs: {str(e)}")
            return []
    
    def _update_apis_status(self) -> None:
        """Atualiza status de todas as APIs"""
        try:
            connectivity_results = self.collector.test_all_connectivity()
            
            for api_name, test_result in connectivity_results.get('tests', {}).items():
                is_online = any(test_result.get(key, False) for key in test_result.keys() if key.startswith('api_'))
                error_message = '; '.join(test_result.get('errors', [])) if test_result.get('errors') else None
                
                self.storage.update_api_status(api_name, is_online, error_message=error_message)
                
        except Exception as e:
            self.logger.error(f"Erro ao atualizar status das APIs: {str(e)}")
    
    def start_auto_collection(self) -> bool:
        """
        Inicia coleta automática em background
        
        Returns:
            True se iniciado com sucesso
        """
        if self.is_running:
            self.logger.warning("Coleta automática já está rodando")
            return False
        
        if not self.enable_auto_collection:
            self.logger.warning("Coleta automática está desabilitada")
            return False
        
        try:
            self.is_running = True
            self.collection_thread = threading.Thread(target=self._auto_collection_loop, daemon=True)
            self.collection_thread.start()
            
            self.logger.info(f"Coleta automática iniciada. Intervalo: {self.auto_collection_interval}s")
            self.storage.log('INFO', 'data_service', 'Coleta automática iniciada')
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar coleta automática: {str(e)}")
            self.is_running = False
            return False
    
    def stop_auto_collection(self) -> bool:
        """
        Para coleta automática
        
        Returns:
            True se parado com sucesso
        """
        if not self.is_running:
            self.logger.warning("Coleta automática não está rodando")
            return False
        
        try:
            self.is_running = False
            
            if self.collection_thread and self.collection_thread.is_alive():
                self.collection_thread.join(timeout=5)
            
            self.logger.info("Coleta automática parada")
            self.storage.log('INFO', 'data_service', 'Coleta automática parada')
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao parar coleta automática: {str(e)}")
            return False
    
    def _auto_collection_loop(self) -> None:
        """Loop principal da coleta automática"""
        while self.is_running:
            try:
                self.logger.info("Executando coleta automática")
                result = self.collect_and_process()
                
                if result['success']:
                    self.logger.info("Coleta automática concluída com sucesso")
                else:
                    self.logger.warning(f"Coleta automática falhou: {result['errors']}")
                
                # Aguarda próximo ciclo
                for _ in range(self.auto_collection_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Erro no loop de coleta automática: {str(e)}")
                self.storage.log('ERROR', 'data_service', f"Erro no loop de coleta automática: {str(e)}")
                
                # Aguarda antes de tentar novamente
                time.sleep(60)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do serviço"""
        try:
            storage_stats = self.storage.get_storage_stats()
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'service_status': {
                    'is_running': self.is_running,
                    'auto_collection_enabled': self.enable_auto_collection,
                    'auto_collection_interval': self.auto_collection_interval,
                    'last_collection': self.last_collection.isoformat() if self.last_collection else None
                },
                'storage_stats': storage_stats,
                'collector_config': {
                    'parallel_execution': self.collector.parallel_execution if self.collector else None,
                    'max_workers': self.collector.max_workers if self.collector else None,
                    'timeout': self.collector.timeout if self.collector else None
                }
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas do serviço: {str(e)}")
            return {'error': str(e)}


if __name__ == "__main__":
    # Teste básico do serviço
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_service.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    config = {
        'enable_auto_collection': False,
        'auto_collection_interval': 300,  # 5 minutos para teste
        'collector': {
            'parallel_execution': True,
            'max_workers': 2
        }
    }
    
    service = DataService(app, config)
    
    with app.app_context():
        print("=== Teste do DataService ===")
        
        # Teste de coleta e processamento
        result = service.collect_and_process(save_to_db=True, use_cache=False)
        print(f"Coleta concluída: {result['success']}")
        print(f"Duração: {result['duration_seconds']}s")
        
        if result['errors']:
            print(f"Erros: {result['errors']}")
        
        # Estatísticas
        stats = service.get_service_stats()
        print(f"Estatísticas: {stats['storage_stats']}")

