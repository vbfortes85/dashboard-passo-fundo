"""
Sistema de alertas para monitoramento de APIs e coletas
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class AlertLevel(Enum):
    """Níveis de alerta"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertType(Enum):
    """Tipos de alerta"""
    API_DOWN = "api_down"
    API_SLOW = "api_slow"
    COLLECTION_FAILED = "collection_failed"
    COLLECTION_SUCCESS = "collection_success"
    DATA_QUALITY = "data_quality"
    SYSTEM_ERROR = "system_error"
    STORAGE_FULL = "storage_full"

class Alert:
    """Classe para representar um alerta"""
    
    def __init__(self, alert_type: AlertType, level: AlertLevel, title: str, 
                 message: str, details: Optional[Dict[str, Any]] = None):
        self.id = f"{alert_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.alert_type = alert_type
        self.level = level
        self.title = title
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        self.acknowledged = False
        self.resolved = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte alerta para dicionário"""
        return {
            'id': self.id,
            'alert_type': self.alert_type.value,
            'level': self.level.value,
            'title': self.title,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged,
            'resolved': self.resolved
        }
    
    def acknowledge(self) -> None:
        """Marca alerta como reconhecido"""
        self.acknowledged = True
    
    def resolve(self) -> None:
        """Marca alerta como resolvido"""
        self.resolved = True
        self.acknowledged = True

class AlertManager:
    """Gerenciador de alertas do sistema"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Armazenamento de alertas em memória
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        
        # Configurações de alerta
        self.max_active_alerts = self.config.get('max_active_alerts', 100)
        self.max_history_alerts = self.config.get('max_history_alerts', 1000)
        
        # Configurações de email (se disponível)
        self.email_config = self.config.get('email', {})
        self.email_enabled = bool(self.email_config.get('enabled', False))
        
        # Handlers de alerta
        self.alert_handlers: Dict[AlertType, List[Callable]] = {}
        
        # Configurações de threshold
        self.api_response_threshold = self.config.get('api_response_threshold', 5000)  # 5s
        self.consecutive_failures_threshold = self.config.get('consecutive_failures_threshold', 3)
        
        self.logger.info("AlertManager inicializado")
    
    def create_alert(self, alert_type: AlertType, level: AlertLevel, title: str, 
                    message: str, details: Optional[Dict[str, Any]] = None) -> Alert:
        """
        Cria um novo alerta
        
        Args:
            alert_type: Tipo do alerta
            level: Nível de severidade
            title: Título do alerta
            message: Mensagem descritiva
            details: Detalhes adicionais
            
        Returns:
            Alerta criado
        """
        alert = Alert(alert_type, level, title, message, details)
        
        # Adiciona à lista de alertas ativos
        self.active_alerts.append(alert)
        
        # Limita número de alertas ativos
        if len(self.active_alerts) > self.max_active_alerts:
            oldest_alert = self.active_alerts.pop(0)
            self.alert_history.append(oldest_alert)
        
        # Executa handlers específicos
        self._execute_handlers(alert)
        
        # Log do alerta
        self.logger.log(
            self._get_log_level(level),
            f"Alerta criado: {title} - {message}",
            extra={'alert_id': alert.id, 'alert_type': alert_type.value}
        )
        
        return alert
    
    def _get_log_level(self, alert_level: AlertLevel) -> int:
        """Converte nível de alerta para nível de log"""
        mapping = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }
        return mapping.get(alert_level, logging.INFO)
    
    def register_handler(self, alert_type: AlertType, handler: Callable[[Alert], None]) -> None:
        """
        Registra handler para tipo específico de alerta
        
        Args:
            alert_type: Tipo de alerta
            handler: Função que será chamada quando o alerta for criado
        """
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []
        
        self.alert_handlers[alert_type].append(handler)
        self.logger.info(f"Handler registrado para {alert_type.value}")
    
    def _execute_handlers(self, alert: Alert) -> None:
        """Executa handlers registrados para o tipo de alerta"""
        handlers = self.alert_handlers.get(alert.alert_type, [])
        
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Erro ao executar handler para {alert.alert_type.value}: {str(e)}")
    
    def check_api_status(self, api_name: str, is_online: bool, response_time_ms: Optional[float] = None,
                        consecutive_failures: int = 0) -> None:
        """
        Verifica status de API e cria alertas se necessário
        
        Args:
            api_name: Nome da API
            is_online: Se a API está online
            response_time_ms: Tempo de resposta em ms
            consecutive_failures: Número de falhas consecutivas
        """
        # Alerta para API offline
        if not is_online:
            if consecutive_failures >= self.consecutive_failures_threshold:
                self.create_alert(
                    AlertType.API_DOWN,
                    AlertLevel.CRITICAL,
                    f"API {api_name} Offline",
                    f"A API {api_name} está offline há {consecutive_failures} tentativas consecutivas",
                    {
                        'api_name': api_name,
                        'consecutive_failures': consecutive_failures,
                        'timestamp': datetime.now().isoformat()
                    }
                )
            else:
                self.create_alert(
                    AlertType.API_DOWN,
                    AlertLevel.WARNING,
                    f"API {api_name} Indisponível",
                    f"A API {api_name} não está respondendo",
                    {
                        'api_name': api_name,
                        'consecutive_failures': consecutive_failures,
                        'timestamp': datetime.now().isoformat()
                    }
                )
        
        # Alerta para API lenta
        elif response_time_ms and response_time_ms > self.api_response_threshold:
            self.create_alert(
                AlertType.API_SLOW,
                AlertLevel.WARNING,
                f"API {api_name} Lenta",
                f"A API {api_name} está respondendo lentamente ({response_time_ms:.0f}ms)",
                {
                    'api_name': api_name,
                    'response_time_ms': response_time_ms,
                    'threshold': self.api_response_threshold,
                    'timestamp': datetime.now().isoformat()
                }
            )
    
    def check_collection_result(self, collection_result: Dict[str, Any]) -> None:
        """
        Verifica resultado de coleta e cria alertas se necessário
        
        Args:
            collection_result: Resultado da coleta de dados
        """
        success = collection_result.get('success', False)
        errors = collection_result.get('errors', [])
        warnings = collection_result.get('warnings', [])
        
        if success:
            # Alerta de sucesso (informativo)
            summary = collection_result.get('collection_results', {}).get('summary', {})
            successful_sources = summary.get('successful', 0)
            total_sources = summary.get('total_sources', 0)
            
            self.create_alert(
                AlertType.COLLECTION_SUCCESS,
                AlertLevel.INFO,
                "Coleta Concluída com Sucesso",
                f"Coleta executada com sucesso: {successful_sources}/{total_sources} fontes coletadas",
                {
                    'successful_sources': successful_sources,
                    'total_sources': total_sources,
                    'duration_seconds': collection_result.get('duration_seconds', 0),
                    'timestamp': collection_result.get('timestamp')
                }
            )
            
            # Alertas para warnings
            if warnings:
                self.create_alert(
                    AlertType.DATA_QUALITY,
                    AlertLevel.WARNING,
                    "Problemas de Qualidade dos Dados",
                    f"Encontrados {len(warnings)} avisos durante a coleta",
                    {
                        'warnings': warnings,
                        'timestamp': collection_result.get('timestamp')
                    }
                )
        else:
            # Alerta de falha na coleta
            self.create_alert(
                AlertType.COLLECTION_FAILED,
                AlertLevel.ERROR,
                "Falha na Coleta de Dados",
                f"A coleta de dados falhou: {'; '.join(errors) if errors else 'Erro desconhecido'}",
                {
                    'errors': errors,
                    'warnings': warnings,
                    'duration_seconds': collection_result.get('duration_seconds', 0),
                    'timestamp': collection_result.get('timestamp')
                }
            )
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None, 
                         alert_type: Optional[AlertType] = None) -> List[Dict[str, Any]]:
        """
        Obtém alertas ativos
        
        Args:
            level: Filtrar por nível (opcional)
            alert_type: Filtrar por tipo (opcional)
            
        Returns:
            Lista de alertas ativos
        """
        alerts = self.active_alerts
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        return [alert.to_dict() for alert in alerts]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Obtém resumo dos alertas
        
        Returns:
            Resumo dos alertas por nível e tipo
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_active': len(self.active_alerts),
            'total_history': len(self.alert_history),
            'by_level': {level.value: 0 for level in AlertLevel},
            'by_type': {alert_type.value: 0 for alert_type in AlertType},
            'unacknowledged': 0,
            'unresolved': 0
        }
        
        for alert in self.active_alerts:
            summary['by_level'][alert.level.value] += 1
            summary['by_type'][alert.alert_type.value] += 1
            
            if not alert.acknowledged:
                summary['unacknowledged'] += 1
            
            if not alert.resolved:
                summary['unresolved'] += 1
        
        return summary
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Reconhece um alerta
        
        Args:
            alert_id: ID do alerta
            
        Returns:
            True se alerta foi encontrado e reconhecido
        """
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.acknowledge()
                self.logger.info(f"Alerta {alert_id} reconhecido")
                return True
        
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve um alerta
        
        Args:
            alert_id: ID do alerta
            
        Returns:
            True se alerta foi encontrado e resolvido
        """
        for i, alert in enumerate(self.active_alerts):
            if alert.id == alert_id:
                alert.resolve()
                # Move para histórico
                resolved_alert = self.active_alerts.pop(i)
                self.alert_history.append(resolved_alert)
                
                # Limita histórico
                if len(self.alert_history) > self.max_history_alerts:
                    self.alert_history.pop(0)
                
                self.logger.info(f"Alerta {alert_id} resolvido")
                return True
        
        return False
    
    def send_email_alert(self, alert: Alert) -> bool:
        """
        Envia alerta por email (se configurado)
        
        Args:
            alert: Alerta a ser enviado
            
        Returns:
            True se email foi enviado com sucesso
        """
        if not self.email_enabled:
            return False
        
        try:
            smtp_server = self.email_config.get('smtp_server')
            smtp_port = self.email_config.get('smtp_port', 587)
            username = self.email_config.get('username')
            password = self.email_config.get('password')
            from_email = self.email_config.get('from_email')
            to_emails = self.email_config.get('to_emails', [])
            
            if not all([smtp_server, username, password, from_email, to_emails]):
                self.logger.warning("Configuração de email incompleta")
                return False
            
            # Cria mensagem
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"[Dashboard Passo Fundo] {alert.title}"
            
            # Corpo do email
            body = f"""
            Alerta: {alert.title}
            Nível: {alert.level.value.upper()}
            Tipo: {alert.alert_type.value}
            Timestamp: {alert.timestamp.strftime('%d/%m/%Y %H:%M:%S')}
            
            Mensagem:
            {alert.message}
            
            Detalhes:
            {json.dumps(alert.details, indent=2, ensure_ascii=False)}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Envia email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email de alerta enviado para {len(to_emails)} destinatários")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao enviar email de alerta: {str(e)}")
            return False
    
    def cleanup_old_alerts(self, days_to_keep: int = 7) -> int:
        """
        Remove alertas antigos do histórico
        
        Args:
            days_to_keep: Número de dias para manter no histórico
            
        Returns:
            Número de alertas removidos
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        original_count = len(self.alert_history)
        self.alert_history = [
            alert for alert in self.alert_history 
            if alert.timestamp > cutoff_date
        ]
        
        removed_count = original_count - len(self.alert_history)
        
        if removed_count > 0:
            self.logger.info(f"Removidos {removed_count} alertas antigos do histórico")
        
        return removed_count


# Handlers de exemplo
def email_handler(alert: Alert) -> None:
    """Handler que envia alertas críticos por email"""
    if alert.level in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
        # Aqui seria implementado o envio de email
        print(f"EMAIL ALERT: {alert.title} - {alert.message}")

def log_handler(alert: Alert) -> None:
    """Handler que registra todos os alertas em log"""
    logger = logging.getLogger('alerts')
    logger.log(
        logging.ERROR if alert.level in [AlertLevel.ERROR, AlertLevel.CRITICAL] else logging.WARNING,
        f"ALERT: {alert.title} - {alert.message}",
        extra={'alert_id': alert.id, 'alert_type': alert.alert_type.value}
    )


if __name__ == "__main__":
    # Teste do sistema de alertas
    config = {
        'max_active_alerts': 50,
        'api_response_threshold': 3000,
        'consecutive_failures_threshold': 2
    }
    
    alert_manager = AlertManager(config)
    
    # Registra handlers
    alert_manager.register_handler(AlertType.API_DOWN, email_handler)
    alert_manager.register_handler(AlertType.COLLECTION_FAILED, log_handler)
    
    # Testa criação de alertas
    alert_manager.check_api_status('ibge', False, consecutive_failures=3)
    alert_manager.check_api_status('bcb', True, response_time_ms=4000)
    
    # Testa resultado de coleta
    collection_result = {
        'success': True,
        'warnings': ['Alguns dados podem estar incompletos'],
        'collection_results': {
            'summary': {
                'successful': 3,
                'total_sources': 4
            }
        },
        'duration_seconds': 45.2,
        'timestamp': datetime.now().isoformat()
    }
    
    alert_manager.check_collection_result(collection_result)
    
    # Mostra resumo
    summary = alert_manager.get_alert_summary()
    print(f"Resumo dos alertas: {summary}")
    
    # Lista alertas ativos
    active_alerts = alert_manager.get_active_alerts()
    print(f"Alertas ativos: {len(active_alerts)}")
    for alert in active_alerts:
        print(f"- {alert['title']} ({alert['level']})")

