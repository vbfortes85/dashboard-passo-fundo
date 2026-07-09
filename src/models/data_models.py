"""
Modelos de dados para armazenamento das informações coletadas
"""

from src.models.user import db  # Usa a mesma instância do SQLAlchemy
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

class CollectionRun(db.Model):
    """Modelo para registrar execuções de coleta"""
    __tablename__ = 'collection_runs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    execution_mode = db.Column(db.String(20), nullable=False)  # 'parallel' ou 'sequential'
    total_sources = db.Column(db.Integer, nullable=False)
    successful_sources = db.Column(db.Integer, nullable=False)
    failed_sources = db.Column(db.Integer, nullable=False)
    total_duration_seconds = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'completed', 'failed', 'partial'
    
    # Relacionamentos
    source_results = db.relationship('SourceResult', backref='collection_run', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'execution_mode': self.execution_mode,
            'total_sources': self.total_sources,
            'successful_sources': self.successful_sources,
            'failed_sources': self.failed_sources,
            'total_duration_seconds': self.total_duration_seconds,
            'status': self.status,
            'success_rate': (self.successful_sources / max(self.total_sources, 1)) * 100
        }

class SourceResult(db.Model):
    """Modelo para resultados de coleta por fonte"""
    __tablename__ = 'source_results'
    
    id = db.Column(db.Integer, primary_key=True)
    collection_run_id = db.Column(db.Integer, db.ForeignKey('collection_runs.id'), nullable=False)
    source_name = db.Column(db.String(50), nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    duration_seconds = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    data_entries = db.relationship('DataEntry', backref='source_result', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'collection_run_id': self.collection_run_id,
            'source_name': self.source_name,
            'success': self.success,
            'duration_seconds': self.duration_seconds,
            'timestamp': self.timestamp.isoformat(),
            'error_message': self.error_message,
            'data_entries_count': len(self.data_entries)
        }

class DataEntry(db.Model):
    """Modelo para armazenar dados coletados"""
    __tablename__ = 'data_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    source_result_id = db.Column(db.Integer, db.ForeignKey('source_results.id'), nullable=False)
    data_type = db.Column(db.String(100), nullable=False)  # 'municipio_info', 'populacao', 'ipca', etc.
    data_key = db.Column(db.String(200), nullable=True)  # Chave específica dos dados
    raw_data = db.Column(db.Text, nullable=False)  # JSON dos dados brutos
    processed_data = db.Column(db.Text, nullable=True)  # JSON dos dados processados
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)
    
    # Índices para otimização de consultas
    __table_args__ = (
        db.Index('idx_data_type_timestamp', 'data_type', 'timestamp'),
        db.Index('idx_data_key_timestamp', 'data_key', 'timestamp'),
    )
    
    def get_raw_data(self) -> Dict[str, Any]:
        """Retorna dados brutos como dicionário"""
        try:
            return json.loads(self.raw_data) if self.raw_data else {}
        except json.JSONDecodeError:
            return {}
    
    def set_raw_data(self, data: Dict[str, Any]) -> None:
        """Define dados brutos a partir de dicionário"""
        self.raw_data = json.dumps(data, ensure_ascii=False)
    
    def get_processed_data(self) -> Optional[Dict[str, Any]]:
        """Retorna dados processados como dicionário"""
        try:
            return json.loads(self.processed_data) if self.processed_data else None
        except json.JSONDecodeError:
            return None
    
    def set_processed_data(self, data: Dict[str, Any]) -> None:
        """Define dados processados a partir de dicionário"""
        self.processed_data = json.dumps(data, ensure_ascii=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'source_result_id': self.source_result_id,
            'data_type': self.data_type,
            'data_key': self.data_key,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'has_processed_data': bool(self.processed_data)
        }

class APIStatus(db.Model):
    """Modelo para monitorar status das APIs"""
    __tablename__ = 'api_status'
    
    id = db.Column(db.Integer, primary_key=True)
    api_name = db.Column(db.String(50), nullable=False)
    is_online = db.Column(db.Boolean, nullable=False)
    response_time_ms = db.Column(db.Float, nullable=True)
    last_check = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    consecutive_failures = db.Column(db.Integer, default=0, nullable=False)
    
    # Índice para otimização
    __table_args__ = (
        db.Index('idx_api_name_last_check', 'api_name', 'last_check'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'api_name': self.api_name,
            'is_online': self.is_online,
            'response_time_ms': self.response_time_ms,
            'last_check': self.last_check.isoformat(),
            'error_message': self.error_message,
            'consecutive_failures': self.consecutive_failures,
            'status': 'online' if self.is_online else 'offline'
        }

class DataCache(db.Model):
    """Modelo para cache de dados processados"""
    __tablename__ = 'data_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(200), unique=True, nullable=False)
    data_type = db.Column(db.String(100), nullable=False)
    cached_data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    hit_count = db.Column(db.Integer, default=0, nullable=False)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices para otimização
    __table_args__ = (
        db.Index('idx_cache_key', 'cache_key'),
        db.Index('idx_expires_at', 'expires_at'),
        db.Index('idx_data_type_created', 'data_type', 'created_at'),
    )
    
    def get_cached_data(self) -> Dict[str, Any]:
        """Retorna dados do cache como dicionário"""
        try:
            return json.loads(self.cached_data) if self.cached_data else {}
        except json.JSONDecodeError:
            return {}
    
    def set_cached_data(self, data: Dict[str, Any]) -> None:
        """Define dados do cache a partir de dicionário"""
        self.cached_data = json.dumps(data, ensure_ascii=False)
    
    def is_expired(self) -> bool:
        """Verifica se o cache expirou"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def update_access(self) -> None:
        """Atualiza estatísticas de acesso"""
        self.hit_count += 1
        self.last_accessed = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'cache_key': self.cache_key,
            'data_type': self.data_type,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'hit_count': self.hit_count,
            'last_accessed': self.last_accessed.isoformat(),
            'is_expired': self.is_expired()
        }

class SystemLog(db.Model):
    """Modelo para logs do sistema"""
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    level = db.Column(db.String(20), nullable=False)  # 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    component = db.Column(db.String(100), nullable=False)  # 'collector', 'processor', 'api', etc.
    message = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON com detalhes adicionais
    
    # Índices para otimização
    __table_args__ = (
        db.Index('idx_timestamp_level', 'timestamp', 'level'),
        db.Index('idx_component_timestamp', 'component', 'timestamp'),
    )
    
    def get_details(self) -> Optional[Dict[str, Any]]:
        """Retorna detalhes como dicionário"""
        try:
            return json.loads(self.details) if self.details else None
        except json.JSONDecodeError:
            return None
    
    def set_details(self, details: Dict[str, Any]) -> None:
        """Define detalhes a partir de dicionário"""
        self.details = json.dumps(details, ensure_ascii=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'component': self.component,
            'message': self.message,
            'details': self.get_details()
        }

# Funções utilitárias para inicialização
def init_db(app):
    """Inicializa o banco de dados"""
    db.init_app(app)
    with app.app_context():
        db.create_all()

def get_latest_data(data_type: str, limit: int = 10) -> list:
    """Obtém os dados mais recentes de um tipo específico"""
    return DataEntry.query.filter_by(data_type=data_type)\
                         .order_by(DataEntry.timestamp.desc())\
                         .limit(limit)\
                         .all()

def get_api_status_summary() -> Dict[str, Any]:
    """Obtém resumo do status de todas as APIs"""
    statuses = APIStatus.query.all()
    
    summary = {
        'total_apis': len(statuses),
        'online_apis': sum(1 for s in statuses if s.is_online),
        'offline_apis': sum(1 for s in statuses if not s.is_online),
        'apis': [s.to_dict() for s in statuses]
    }
    
    summary['availability_percentage'] = (
        (summary['online_apis'] / max(summary['total_apis'], 1)) * 100
    )
    
    return summary

def cleanup_old_data(days_to_keep: int = 30) -> int:
    """Remove dados antigos do banco"""
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    # Remove entradas de dados antigas
    old_entries = DataEntry.query.filter(DataEntry.timestamp < cutoff_date).all()
    count = len(old_entries)
    
    for entry in old_entries:
        db.session.delete(entry)
    
    # Remove cache expirado
    expired_cache = DataCache.query.filter(
        DataCache.expires_at < datetime.utcnow()
    ).all()
    
    for cache in expired_cache:
        db.session.delete(cache)
    
    db.session.commit()
    return count

