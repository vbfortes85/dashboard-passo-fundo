"""
Rotas Flask para o sistema de alertas
"""

from flask import Blueprint, jsonify, request
import logging
from datetime import datetime

from src.alerts.alert_manager import AlertManager, AlertLevel, AlertType

alerts_bp = Blueprint('alerts', __name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instância global do gerenciador de alertas
alert_manager = None

def get_alert_manager():
    """Obtém instância do gerenciador de alertas"""
    global alert_manager
    if alert_manager is None:
        config = {
            'max_active_alerts': 100,
            'max_history_alerts': 1000,
            'api_response_threshold': 5000,  # 5 segundos
            'consecutive_failures_threshold': 3,
            'email': {
                'enabled': False  # Desabilitado por padrão
            }
        }
        alert_manager = AlertManager(config)
        
        # Registra handlers básicos
        alert_manager.register_handler(AlertType.API_DOWN, _log_critical_alert)
        alert_manager.register_handler(AlertType.COLLECTION_FAILED, _log_error_alert)
        
    return alert_manager

def _log_critical_alert(alert):
    """Handler para alertas críticos"""
    logger.critical(f"ALERTA CRÍTICO: {alert.title} - {alert.message}")

def _log_error_alert(alert):
    """Handler para alertas de erro"""
    logger.error(f"ALERTA DE ERRO: {alert.title} - {alert.message}")

@alerts_bp.route('/summary', methods=['GET'])
def get_alert_summary():
    """Obtém resumo dos alertas"""
    try:
        manager = get_alert_manager()
        summary = manager.get_alert_summary()
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Erro ao obter resumo de alertas: {str(e)}")
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/active', methods=['GET'])
def get_active_alerts():
    """Obtém alertas ativos"""
    try:
        manager = get_alert_manager()
        
        # Parâmetros de filtro opcionais
        level_param = request.args.get('level')
        type_param = request.args.get('type')
        
        level = None
        if level_param:
            try:
                level = AlertLevel(level_param.lower())
            except ValueError:
                return jsonify({'error': f'Nível inválido: {level_param}'}), 400
        
        alert_type = None
        if type_param:
            try:
                alert_type = AlertType(type_param.lower())
            except ValueError:
                return jsonify({'error': f'Tipo inválido: {type_param}'}), 400
        
        alerts = manager.get_active_alerts(level=level, alert_type=alert_type)
        
        return jsonify({
            'count': len(alerts),
            'alerts': alerts,
            'filters': {
                'level': level_param,
                'type': type_param
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter alertas ativos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/create', methods=['POST'])
def create_alert():
    """Cria um novo alerta manualmente"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Validação dos campos obrigatórios
        required_fields = ['type', 'level', 'title', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
        
        # Converte strings para enums
        try:
            alert_type = AlertType(data['type'].lower())
            alert_level = AlertLevel(data['level'].lower())
        except ValueError as e:
            return jsonify({'error': f'Valor inválido: {str(e)}'}), 400
        
        manager = get_alert_manager()
        alert = manager.create_alert(
            alert_type=alert_type,
            level=alert_level,
            title=data['title'],
            message=data['message'],
            details=data.get('details')
        )
        
        return jsonify({
            'message': 'Alerta criado com sucesso',
            'alert': alert.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar alerta: {str(e)}")
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/<alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Reconhece um alerta"""
    try:
        manager = get_alert_manager()
        success = manager.acknowledge_alert(alert_id)
        
        if success:
            return jsonify({
                'message': f'Alerta {alert_id} reconhecido com sucesso',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': 'Alerta não encontrado'}), 404
            
    except Exception as e:
        logger.error(f"Erro ao reconhecer alerta {alert_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/<alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """Resolve um alerta"""
    try:
        manager = get_alert_manager()
        success = manager.resolve_alert(alert_id)
        
        if success:
            return jsonify({
                'message': f'Alerta {alert_id} resolvido com sucesso',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': 'Alerta não encontrado'}), 404
            
    except Exception as e:
        logger.error(f"Erro ao resolver alerta {alert_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/check-apis', methods=['POST'])
def check_apis_status():
    """Verifica status das APIs e cria alertas se necessário"""
    try:
        data = request.get_json()
        if not data or 'apis' not in data:
            return jsonify({'error': 'Lista de APIs não fornecida'}), 400
        
        manager = get_alert_manager()
        alerts_created = 0
        
        for api_data in data['apis']:
            api_name = api_data.get('api_name')
            is_online = api_data.get('is_online', False)
            response_time_ms = api_data.get('response_time_ms')
            consecutive_failures = api_data.get('consecutive_failures', 0)
            
            if api_name:
                manager.check_api_status(
                    api_name=api_name,
                    is_online=is_online,
                    response_time_ms=response_time_ms,
                    consecutive_failures=consecutive_failures
                )
                alerts_created += 1
        
        return jsonify({
            'message': f'Verificação de {alerts_created} APIs concluída',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar status das APIs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/check-collection', methods=['POST'])
def check_collection_result():
    """Verifica resultado de coleta e cria alertas se necessário"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Resultado de coleta não fornecido'}), 400
        
        manager = get_alert_manager()
        manager.check_collection_result(data)
        
        return jsonify({
            'message': 'Verificação de resultado de coleta concluída',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar resultado de coleta: {str(e)}")
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/cleanup', methods=['POST'])
def cleanup_old_alerts():
    """Remove alertas antigos do histórico"""
    try:
        data = request.get_json() or {}
        days_to_keep = data.get('days_to_keep', 7)
        
        if not isinstance(days_to_keep, int) or days_to_keep < 1:
            return jsonify({'error': 'days_to_keep deve ser um inteiro positivo'}), 400
        
        manager = get_alert_manager()
        removed_count = manager.cleanup_old_alerts(days_to_keep)
        
        return jsonify({
            'message': f'Limpeza concluída: {removed_count} alertas removidos',
            'days_to_keep': days_to_keep,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro na limpeza de alertas: {str(e)}")
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/config', methods=['GET'])
def get_alert_config():
    """Obtém configuração atual do sistema de alertas"""
    try:
        manager = get_alert_manager()
        
        config_info = {
            'max_active_alerts': manager.max_active_alerts,
            'max_history_alerts': manager.max_history_alerts,
            'api_response_threshold': manager.api_response_threshold,
            'consecutive_failures_threshold': manager.consecutive_failures_threshold,
            'email_enabled': manager.email_enabled,
            'handlers_registered': {
                alert_type.value: len(handlers) 
                for alert_type, handlers in manager.alert_handlers.items()
            }
        }
        
        return jsonify(config_info)
        
    except Exception as e:
        logger.error(f"Erro ao obter configuração de alertas: {str(e)}")
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/test', methods=['POST'])
def test_alert_system():
    """Cria alertas de teste para verificar o sistema"""
    try:
        manager = get_alert_manager()
        
        # Cria alguns alertas de teste
        test_alerts = [
            {
                'type': AlertType.API_DOWN,
                'level': AlertLevel.WARNING,
                'title': 'Teste - API Indisponível',
                'message': 'Este é um alerta de teste para API indisponível',
                'details': {'test': True, 'api_name': 'test_api'}
            },
            {
                'type': AlertType.COLLECTION_SUCCESS,
                'level': AlertLevel.INFO,
                'title': 'Teste - Coleta Bem-sucedida',
                'message': 'Este é um alerta de teste para coleta bem-sucedida',
                'details': {'test': True, 'sources': 4}
            },
            {
                'type': AlertType.DATA_QUALITY,
                'level': AlertLevel.WARNING,
                'title': 'Teste - Qualidade dos Dados',
                'message': 'Este é um alerta de teste para problemas de qualidade',
                'details': {'test': True, 'warnings': ['Dados incompletos']}
            }
        ]
        
        created_alerts = []
        for alert_data in test_alerts:
            alert = manager.create_alert(
                alert_type=alert_data['type'],
                level=alert_data['level'],
                title=alert_data['title'],
                message=alert_data['message'],
                details=alert_data['details']
            )
            created_alerts.append(alert.to_dict())
        
        return jsonify({
            'message': f'{len(created_alerts)} alertas de teste criados',
            'alerts': created_alerts,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar alertas de teste: {str(e)}")
        return jsonify({'error': str(e)}), 500

@alerts_bp.errorhandler(404)
def not_found(error):
    """Handler para rotas não encontradas"""
    return jsonify({'error': 'Endpoint de alertas não encontrado'}), 404

@alerts_bp.errorhandler(500)
def internal_error(error):
    """Handler para erros internos"""
    return jsonify({'error': 'Erro interno no sistema de alertas'}), 500

