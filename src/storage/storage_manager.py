"""
Sistema de armazenamento e cache para dados coletados
Gerencia persistência, cache e recuperação de dados
"""

import logging
import json
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.exc import SQLAlchemyError

from src.models.data_models import (
    db, CollectionRun, SourceResult, DataEntry, APIStatus, 
    DataCache, SystemLog
)

class StorageManager:
    """Gerenciador de armazenamento e cache de dados"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        
        # Configurações de cache
        self.default_cache_ttl = timedelta(hours=1)  # TTL padrão do cache
        self.max_cache_entries = 1000  # Máximo de entradas no cache
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa o gerenciador com a aplicação Flask"""
        self.app = app
        # O banco já foi inicializado no main.py, não precisa criar novamente
    
    def store_collection_results(self, results: Dict[str, Any], processed_data: Optional[Dict[str, Any]] = None) -> int:
        """
        Armazena resultados de uma coleta completa
        
        Args:
            results: Resultados brutos da coleta
            processed_data: Dados processados (opcional)
            
        Returns:
            ID da execução de coleta criada
        """
        try:
            # Cria registro da execução de coleta
            summary = results.get('summary', {})
            collection_run = CollectionRun(
                execution_mode=results.get('execution_mode', 'unknown'),
                total_sources=summary.get('total_sources', 0),
                successful_sources=summary.get('successful', 0),
                failed_sources=summary.get('failed', 0),
                total_duration_seconds=summary.get('total_duration_seconds', 0),
                status='completed' if summary.get('successful', 0) > 0 else 'failed'
            )
            
            db.session.add(collection_run)
            db.session.flush()  # Para obter o ID
            
            # Armazena resultados por fonte
            for source_name, source_data in results.get('sources', {}).items():
                source_result = SourceResult(
                    collection_run_id=collection_run.id,
                    source_name=source_name,
                    success=source_data.get('success', False),
                    duration_seconds=source_data.get('duration_seconds', 0),
                    error_message=source_data.get('error')
                )
                
                db.session.add(source_result)
                db.session.flush()  # Para obter o ID
                
                # Armazena dados individuais se a coleta foi bem-sucedida
                if source_result.success and 'data' in source_data:
                    self._store_source_data_entries(source_result.id, source_name, source_data['data'])
                
                # Armazena dados processados se disponíveis
                if processed_data and source_name in processed_data.get('processed_sources', {}):
                    processed_source = processed_data['processed_sources'][source_name]
                    if processed_source.get('normalized_data'):
                        self._store_processed_data_entries(source_result.id, source_name, processed_source['normalized_data'])
            
            db.session.commit()
            
            self.logger.info(f"Resultados de coleta armazenados. ID da execução: {collection_run.id}")
            return collection_run.id
            
        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Erro ao armazenar resultados de coleta: {str(e)}")
            raise
    
    def _store_source_data_entries(self, source_result_id: int, source_name: str, data: Dict[str, Any]) -> None:
        """Armazena entradas de dados brutos de uma fonte"""
        for data_key, data_value in data.items():
            if data_value is not None:
                data_entry = DataEntry(
                    source_result_id=source_result_id,
                    data_type=f"{source_name}_{data_key}",
                    data_key=data_key,
                    raw_data=json.dumps(data_value, ensure_ascii=False)
                )
                db.session.add(data_entry)
    
    def _store_processed_data_entries(self, source_result_id: int, source_name: str, normalized_data: Dict[str, Any]) -> None:
        """Armazena entradas de dados processados de uma fonte"""
        for data_key, data_value in normalized_data.items():
            if data_value is not None:
                # Busca entrada existente ou cria nova
                existing_entry = DataEntry.query.filter_by(
                    source_result_id=source_result_id,
                    data_key=data_key
                ).first()
                
                if existing_entry:
                    existing_entry.set_processed_data(data_value)
                else:
                    data_entry = DataEntry(
                        source_result_id=source_result_id,
                        data_type=f"{source_name}_{data_key}_processed",
                        data_key=data_key,
                        raw_data='{}',  # Dados processados não têm raw_data
                        processed_data=json.dumps(data_value, ensure_ascii=False)
                    )
                    db.session.add(data_entry)
    
    def get_latest_data(self, data_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém os dados mais recentes de um tipo específico
        
        Args:
            data_type: Tipo de dados a buscar
            limit: Número máximo de registros
            
        Returns:
            Lista de dados encontrados
        """
        try:
            entries = DataEntry.query.filter_by(data_type=data_type)\
                                   .order_by(desc(DataEntry.timestamp))\
                                   .limit(limit)\
                                   .all()
            
            results = []
            for entry in entries:
                result = entry.to_dict()
                result['raw_data'] = entry.get_raw_data()
                result['processed_data'] = entry.get_processed_data()
                results.append(result)
            
            return results
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar dados do tipo {data_type}: {str(e)}")
            return []
    
    def get_data_by_key(self, data_key: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém dados por chave específica
        
        Args:
            data_key: Chave dos dados
            limit: Número máximo de registros
            
        Returns:
            Lista de dados encontrados
        """
        try:
            entries = DataEntry.query.filter_by(data_key=data_key)\
                                   .order_by(desc(DataEntry.timestamp))\
                                   .limit(limit)\
                                   .all()
            
            results = []
            for entry in entries:
                result = entry.to_dict()
                result['raw_data'] = entry.get_raw_data()
                result['processed_data'] = entry.get_processed_data()
                results.append(result)
            
            return results
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar dados com chave {data_key}: {str(e)}")
            return []
    
    def get_collection_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Obtém histórico de coletas
        
        Args:
            limit: Número máximo de registros
            
        Returns:
            Lista de execuções de coleta
        """
        try:
            runs = CollectionRun.query.order_by(desc(CollectionRun.timestamp))\
                                     .limit(limit)\
                                     .all()
            
            return [run.to_dict() for run in runs]
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar histórico de coletas: {str(e)}")
            return []
    
    def get_collection_details(self, collection_run_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém detalhes de uma coleta específica
        
        Args:
            collection_run_id: ID da execução de coleta
            
        Returns:
            Detalhes da coleta ou None se não encontrada
        """
        try:
            run = CollectionRun.query.get(collection_run_id)
            if not run:
                return None
            
            details = run.to_dict()
            details['source_results'] = []
            
            for source_result in run.source_results:
                source_dict = source_result.to_dict()
                source_dict['data_entries'] = [entry.to_dict() for entry in source_result.data_entries]
                details['source_results'].append(source_dict)
            
            return details
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar detalhes da coleta {collection_run_id}: {str(e)}")
            return None
    
    # Sistema de Cache
    
    def _generate_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """Gera chave única para cache"""
        params_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        hash_obj = hashlib.md5(params_str.encode('utf-8'))
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    def cache_set(self, key: str, data: Dict[str, Any], data_type: str, ttl: Optional[timedelta] = None) -> bool:
        """
        Armazena dados no cache
        
        Args:
            key: Chave do cache
            data: Dados a armazenar
            data_type: Tipo dos dados
            ttl: Tempo de vida do cache
            
        Returns:
            True se armazenado com sucesso
        """
        try:
            # Remove entrada existente se houver
            existing = DataCache.query.filter_by(cache_key=key).first()
            if existing:
                db.session.delete(existing)
            
            # Calcula expiração
            expires_at = None
            if ttl:
                expires_at = datetime.utcnow() + ttl
            elif self.default_cache_ttl:
                expires_at = datetime.utcnow() + self.default_cache_ttl
            
            # Cria nova entrada
            cache_entry = DataCache(
                cache_key=key,
                data_type=data_type,
                cached_data=json.dumps(data, ensure_ascii=False),
                expires_at=expires_at
            )
            
            db.session.add(cache_entry)
            db.session.commit()
            
            # Limpa cache antigo se necessário
            self._cleanup_cache()
            
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Erro ao armazenar no cache: {str(e)}")
            return False
    
    def cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Recupera dados do cache
        
        Args:
            key: Chave do cache
            
        Returns:
            Dados do cache ou None se não encontrado/expirado
        """
        try:
            cache_entry = DataCache.query.filter_by(cache_key=key).first()
            
            if not cache_entry:
                return None
            
            # Verifica se expirou
            if cache_entry.is_expired():
                db.session.delete(cache_entry)
                db.session.commit()
                return None
            
            # Atualiza estatísticas de acesso
            cache_entry.update_access()
            db.session.commit()
            
            return cache_entry.get_cached_data()
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao recuperar do cache: {str(e)}")
            return None
    
    def cache_delete(self, key: str) -> bool:
        """
        Remove entrada do cache
        
        Args:
            key: Chave do cache
            
        Returns:
            True se removido com sucesso
        """
        try:
            cache_entry = DataCache.query.filter_by(cache_key=key).first()
            if cache_entry:
                db.session.delete(cache_entry)
                db.session.commit()
                return True
            return False
            
        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Erro ao remover do cache: {str(e)}")
            return False
    
    def _cleanup_cache(self) -> None:
        """Limpa entradas antigas do cache"""
        try:
            # Remove entradas expiradas
            expired_entries = DataCache.query.filter(
                DataCache.expires_at < datetime.utcnow()
            ).all()
            
            for entry in expired_entries:
                db.session.delete(entry)
            
            # Se ainda há muitas entradas, remove as menos acessadas
            total_entries = DataCache.query.count()
            if total_entries > self.max_cache_entries:
                excess = total_entries - self.max_cache_entries
                old_entries = DataCache.query.order_by(DataCache.last_accessed)\
                                           .limit(excess)\
                                           .all()
                
                for entry in old_entries:
                    db.session.delete(entry)
            
            db.session.commit()
            
        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Erro na limpeza do cache: {str(e)}")
    
    # Sistema de Status de APIs
    
    def update_api_status(self, api_name: str, is_online: bool, response_time_ms: Optional[float] = None, 
                         error_message: Optional[str] = None) -> None:
        """
        Atualiza status de uma API
        
        Args:
            api_name: Nome da API
            is_online: Se a API está online
            response_time_ms: Tempo de resposta em ms
            error_message: Mensagem de erro se offline
        """
        try:
            status = APIStatus.query.filter_by(api_name=api_name).first()
            
            if status:
                # Atualiza status existente
                previous_online = status.is_online
                status.is_online = is_online
                status.response_time_ms = response_time_ms
                status.last_check = datetime.utcnow()
                status.error_message = error_message
                
                # Atualiza contador de falhas consecutivas
                if is_online:
                    status.consecutive_failures = 0
                elif not previous_online:
                    status.consecutive_failures += 1
                else:
                    status.consecutive_failures = 1
            else:
                # Cria novo status
                status = APIStatus(
                    api_name=api_name,
                    is_online=is_online,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    consecutive_failures=0 if is_online else 1
                )
                db.session.add(status)
            
            db.session.commit()
            
        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Erro ao atualizar status da API {api_name}: {str(e)}")
    
    def get_apis_status(self) -> List[Dict[str, Any]]:
        """
        Obtém status de todas as APIs
        
        Returns:
            Lista com status das APIs
        """
        try:
            statuses = APIStatus.query.order_by(APIStatus.api_name).all()
            return [status.to_dict() for status in statuses]
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar status das APIs: {str(e)}")
            return []
    
    # Sistema de Logs
    
    def log(self, level: str, component: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Registra log no sistema
        
        Args:
            level: Nível do log (INFO, WARNING, ERROR, CRITICAL)
            component: Componente que gerou o log
            message: Mensagem do log
            details: Detalhes adicionais
        """
        try:
            log_entry = SystemLog(
                level=level.upper(),
                component=component,
                message=message,
                details=json.dumps(details, ensure_ascii=False) if details else None
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Erro ao registrar log: {str(e)}")
    
    def get_logs(self, level: Optional[str] = None, component: Optional[str] = None, 
                limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtém logs do sistema
        
        Args:
            level: Filtrar por nível
            component: Filtrar por componente
            limit: Número máximo de logs
            
        Returns:
            Lista de logs
        """
        try:
            query = SystemLog.query
            
            if level:
                query = query.filter_by(level=level.upper())
            
            if component:
                query = query.filter_by(component=component)
            
            logs = query.order_by(desc(SystemLog.timestamp))\
                       .limit(limit)\
                       .all()
            
            return [log.to_dict() for log in logs]
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar logs: {str(e)}")
            return []
    
    # Utilitários
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do armazenamento"""
        try:
            stats = {
                'collection_runs': CollectionRun.query.count(),
                'source_results': SourceResult.query.count(),
                'data_entries': DataEntry.query.count(),
                'api_statuses': APIStatus.query.count(),
                'cache_entries': DataCache.query.count(),
                'system_logs': SystemLog.query.count(),
                'latest_collection': None,
                'cache_hit_rate': 0
            }
            
            # Última coleta
            latest_run = CollectionRun.query.order_by(desc(CollectionRun.timestamp)).first()
            if latest_run:
                stats['latest_collection'] = latest_run.to_dict()
            
            # Taxa de acerto do cache
            total_cache = DataCache.query.count()
            if total_cache > 0:
                avg_hits = db.session.query(func.avg(DataCache.hit_count)).scalar() or 0
                stats['cache_hit_rate'] = float(avg_hits)
            
            return stats
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {}


if __name__ == "__main__":
    # Teste básico do storage manager
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    storage = StorageManager(app)
    
    with app.app_context():
        # Teste de cache
        test_data = {'test': 'data', 'timestamp': datetime.now().isoformat()}
        storage.cache_set('test_key', test_data, 'test_type')
        
        cached_data = storage.cache_get('test_key')
        print(f"Dados do cache: {cached_data}")
        
        # Teste de log
        storage.log('INFO', 'test', 'Teste do sistema de logs', {'detail': 'teste'})
        
        # Estatísticas
        stats = storage.get_storage_stats()
        print(f"Estatísticas: {stats}")

